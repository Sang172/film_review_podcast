import streamlit as st
import pandas as pd
import pickle
import time
from google.cloud import storage
from src.config import setup_logging, GCS_BUCKET_NAME
from src.config import PODCAST_LENGTH_OPTIONS, LENGTH_PREFERENCE_ORDER, DEFAULT_LENGTH_PREFERENCE
from src.search import get_video_transcripts
from src.review import review_summary_parallel_with_retry, get_final_summary
from src.audio import create_podcast
from youtube_search import YoutubeSearch

logger = setup_logging()

def main(movie: str, allow_spoilers: bool = False, length_preference: str = DEFAULT_LENGTH_PREFERENCE):
    start_time = time.time()
    if allow_spoilers:
        search_term = movie + ' movie spoiler review'
    else:
        search_term = movie + ' movie no spoiler review'
    max_results = 20

    gcs_bucket_name = GCS_BUCKET_NAME
    directory_name = movie.lower().replace(' ', '_')
    spoiler_suffix = "_spoiler" if allow_spoilers else "_no_spoiler"

    try:
        length_options = PODCAST_LENGTH_OPTIONS.get(length_preference, PODCAST_LENGTH_OPTIONS[DEFAULT_LENGTH_PREFERENCE])
        length_suffix = length_options["filename_suffix"]
    except KeyError:
        logger.error(f"Invalid length_preference '{length_preference}' and fallback failed. Using empty suffix.")
        length_suffix = ""

    podcast_gcs_path = f"{directory_name}/{directory_name}{spoiler_suffix}{length_suffix}_podcast.mp3"
    review_gcs_path = f"{directory_name}/{directory_name}{spoiler_suffix}{length_suffix}_review_text.pkl"
    transcripts_gcs_path = f"{directory_name}/{directory_name}{spoiler_suffix}_source_videos.pkl"

    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket_name)

    podcast_blob = bucket.blob(podcast_gcs_path)
    review_blob = bucket.blob(review_gcs_path)
    transcripts_blob = bucket.blob(transcripts_gcs_path)

    cache_log_suffix = f" (spoilers: {allow_spoilers}, length: {length_preference})"

    if podcast_blob.exists() and review_blob.exists() and transcripts_blob.exists():
        logger.info(f"Cache hit for '{movie}'{cache_log_suffix}")
        podcast_bytes = podcast_blob.download_as_bytes()
        review_pickle_bytes = review_blob.download_as_bytes()
        transcripts_pickle_bytes = transcripts_blob.download_as_bytes()

        review = pickle.loads(review_pickle_bytes)
        video_transcripts = pickle.loads(transcripts_pickle_bytes)

        logger.info(f"Successfully loaded cached data for '{movie}'{cache_log_suffix} from GCS.")
        return video_transcripts, review, podcast_bytes

    logger.info(f"Cache miss for '{movie}'{cache_log_suffix}. Generating new review.")

    logger.info(f'Searching YouTube for {"spoiler" if allow_spoilers else "non-spoiler"} reviews on {movie}...')
    videos = YoutubeSearch(search_term, max_results=max_results).to_dict()
    logger.info('Search complete, retrieving transcripts...')
    video_transcripts = get_video_transcripts(videos, movie, allow_spoilers=allow_spoilers)

    if len(video_transcripts) < 2:
        logger.info(f"Not enough reviews found. Trying a more general search...")
        general_search = movie + " movie review"
        additional_videos = YoutubeSearch(general_search, max_results=max_results).to_dict()
        additional_transcripts = get_video_transcripts(additional_videos, movie, allow_spoilers=allow_spoilers)
        existing_ids = {v['url'] for v in video_transcripts}
        for transcript in additional_transcripts:
            if transcript['url'] not in existing_ids:
                video_transcripts.append(transcript)

    logger.info('Retrieval complete, analyzing reviews...')
    reviews = review_summary_parallel_with_retry(video_transcripts, movie, allow_spoilers=allow_spoilers)

    if not reviews:
        logger.error("No valid reviews could be processed")
        return video_transcripts, "No valid reviews could be processed for this movie.", None

    try:
        length_options = PODCAST_LENGTH_OPTIONS.get(length_preference, PODCAST_LENGTH_OPTIONS[DEFAULT_LENGTH_PREFERENCE])
        final_summary_length_instruction = length_options["prompt_instruction"]
    except KeyError:
        logger.error(f"Invalid length_preference '{length_preference}' for final summary. Using default instruction.")
        final_summary_length_instruction = PODCAST_LENGTH_OPTIONS[DEFAULT_LENGTH_PREFERENCE]["prompt_instruction"]

    logger.info(f'Generating final summary with target length: "{final_summary_length_instruction}"')
    review = get_final_summary(
        reviews,
        movie,
        allow_spoilers=allow_spoilers,
        length_prompt_instruction=final_summary_length_instruction
    )

    logger.info('Analysis complete, generating podcast...')

    podcast_bytes = create_podcast(review)
    logger.info(f"Podcast generation complete")

    review_pickle_bytes = pickle.dumps(review)
    transcripts_pickle_bytes = pickle.dumps(video_transcripts)

    podcast_blob.upload_from_string(podcast_bytes, content_type='audio/mpeg')
    review_blob.upload_from_string(review_pickle_bytes, content_type='application/octet-stream')
    transcripts_blob.upload_from_string(transcripts_pickle_bytes, content_type='application/octet-stream')
    logger.info(f"Successfully saved results for '{movie}'{cache_log_suffix} to GCS.")
    logger.info(f"Time taken for '{movie}': {(time.time() - start_time):.2f} seconds")
    return video_transcripts, review, podcast_bytes


@st.cache_data(hash_funcs={bool: lambda x: f"spoiler_{x}"})
def generate_podcast(movie_title, allow_spoilers=False, length_preference: str = DEFAULT_LENGTH_PREFERENCE):
    video_transcripts, review, podcast_bytes = main(
        movie_title,
        allow_spoilers=allow_spoilers,
        length_preference=length_preference
    )
    return video_transcripts, review, podcast_bytes


if __name__ == "__main__":
    st.set_page_config(
        page_title="CineCast AI",
        page_icon="🎬"
    )

    st.title("🎬 CineCast AI")

    st.subheader("Select Podcast Length")

    ordered_labels = [PODCAST_LENGTH_OPTIONS[key]["ui_label"] for key in LENGTH_PREFERENCE_ORDER]
    ordered_keys = LENGTH_PREFERENCE_ORDER

    default_index = ordered_keys.index(DEFAULT_LENGTH_PREFERENCE)

    current_length_key = st.session_state.get("length_preference", DEFAULT_LENGTH_PREFERENCE)
    try:
        current_index = ordered_keys.index(current_length_key)
    except ValueError:
        current_index = default_index

    selected_label = st.selectbox(
        "Choose the desired duration:",
        options=ordered_labels,
        index=current_index,
        help="Select the approximate length for your generated podcast summary.",
        key="length_label_select"
    )

    selected_length_key = next(key for key, val in PODCAST_LENGTH_OPTIONS.items() if val["ui_label"] == selected_label)
    st.session_state.length_preference = selected_length_key

    st.session_state.allow_spoilers = st.toggle(
        "Include Spoilers",
        value=st.session_state.get("allow_spoilers", False),
        help="Toggle ON to include plot details and spoilers. Toggle OFF for a spoiler-free experience.",
        key="spoiler_toggle",
        on_change=lambda: st.session_state.update(allow_spoilers=st.session_state.spoiler_toggle)
    )

    if st.session_state.allow_spoilers:
        st.caption("🚨 Spoiler mode: The review may reveal major plot points and twists")
    else:
        st.caption("✅ Spoiler-free mode: No major plot reveals")

    with st.form(key="podcast_input_form"):
        movie_title = st.text_input("Enter movie title:", key="movie_title_input")
        submitted = st.form_submit_button("Generate Podcast")

    if submitted:
        if not movie_title:
            st.warning("Please enter a movie title first!")
        else:   
            with st.spinner(f"Searching for reviews and generating {'' if st.session_state.allow_spoilers else 'spoiler-free '}podcast for '{movie_title}', may take up to 3 minutes..."):
                video_transcripts, review, podcast_bytes = generate_podcast(
                    movie_title,
                    allow_spoilers=st.session_state.allow_spoilers,
                    length_preference=st.session_state.length_preference
                )

            st.subheader(f"Podcast for '{movie_title}' generated!")
            st.audio(podcast_bytes, format="audio/mp3")

            spoiler_info = "with_spoilers" if st.session_state.allow_spoilers else "spoiler_free"
            length_tag = st.session_state.length_preference.lower()
            download_filename = f"{movie_title.replace(' ','_')}_{spoiler_info}_{length_tag}_podcast.mp3"
            st.download_button(
                label="Download Podcast",
                data=podcast_bytes,
                file_name=download_filename,
                mime="audio/mp3",
            )

            with st.expander("Podcast Transcript"):
                st.write(review)

            with st.expander("Source Videos"):
                video_review_data = []
                for video_info in video_transcripts:
                    spoiler_tag = "🚨 Contains Spoilers" if video_info.get('likely_has_spoilers', False) else "✅ Spoiler-Free"
                    title = video_info['title']
                    creator = video_info['creator']
                    url = video_info['url']
                    markdown_link = f"[{title} by {creator}]({url}) - {spoiler_tag}"
                    video_review_data.append({"Reviews": markdown_link})

                df = pd.DataFrame(video_review_data)
                st.markdown(df.to_markdown(index=False), unsafe_allow_html=True)
            
    st.markdown("---")
    st.caption("Created by: Andrea Quiroz, Nihal Karim, Peeyush Patel, Sang Ahn, Suhho Lee")