import streamlit as st
import pandas as pd
import pickle
import time
from google.cloud import storage
from src.config import setup_logging, GCS_BUCKET_NAME
from src.config import PODCAST_LENGTH_OPTIONS, LENGTH_PREFERENCE_ORDER, DEFAULT_LENGTH_PREFERENCE
from src.search import get_video_transcripts
from src.review import review_summary_parallel_with_retry, get_final_summary
from src.utils import find_similar_movie_imdb
from src.audio import create_podcast
from youtube_search import YoutubeSearch
from dotenv import load_dotenv
import os
#from google.oauth2.service_account import Credentials
from datetime import datetime

load_dotenv()
#credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
#credentials = Credentials.from_service_account_file(credentials_path)

logger = setup_logging()


def main(movie: str, allow_spoilers: bool = False, length_preference: str = DEFAULT_LENGTH_PREFERENCE):
    start_time = time.time()
    if allow_spoilers:
        search_term = movie + ' movie spoiler review'
    else:
        search_term = movie + ' movie no spoiler review'
    max_results = 5

    gcs_bucket_name = GCS_BUCKET_NAME
    directory_name = movie.lower().replace(' ', '_')
    spoiler_suffix = "_spoiler" if allow_spoilers else "_no_spoiler"

    try:
        length_options = PODCAST_LENGTH_OPTIONS.get(
            length_preference, PODCAST_LENGTH_OPTIONS[DEFAULT_LENGTH_PREFERENCE])
        length_suffix = length_options["filename_suffix"]
    except KeyError:
        logger.error(
            f"Invalid length_preference '{length_preference}' and fallback failed. Using empty suffix.")
        length_suffix = ""

    podcast_gcs_path = f"{directory_name}/{directory_name}{spoiler_suffix}{length_suffix}_podcast.mp3"
    review_gcs_path = f"{directory_name}/{directory_name}{spoiler_suffix}{length_suffix}_review_text.pkl"
    transcripts_gcs_path = f"{directory_name}/{directory_name}{spoiler_suffix}_source_videos.pkl"

    #storage_client = storage.Client(credentials=credentials)
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

        logger.info(
            f"Successfully loaded cached data for '{movie}'{cache_log_suffix} from GCS.")
        return video_transcripts, review, podcast_bytes

    logger.info(
        f"Cache miss for '{movie}'{cache_log_suffix}. Generating new review.")

    logger.info(
        f'Searching YouTube for {"spoiler" if allow_spoilers else "non-spoiler"} reviews on {movie}...')
    videos = YoutubeSearch(search_term, max_results=max_results).to_dict()
    logger.info('Search complete, retrieving transcripts...')
    video_transcripts = get_video_transcripts(
        videos, movie, allow_spoilers=allow_spoilers)

    if len(video_transcripts) < 2:
        logger.info(
            f"Not enough reviews found. Trying a more general search...")
        general_search = movie + " movie review"
        additional_videos = YoutubeSearch(
            general_search, max_results=max_results).to_dict()
        additional_transcripts = get_video_transcripts(
            additional_videos, movie, allow_spoilers=allow_spoilers)
        existing_ids = {v['url'] for v in video_transcripts}
        for transcript in additional_transcripts:
            if transcript['url'] not in existing_ids:
                video_transcripts.append(transcript)

    logger.info('Retrieval complete, analyzing reviews...')
    reviews = review_summary_parallel_with_retry(
        video_transcripts, movie, allow_spoilers=allow_spoilers)

    if not reviews:
        logger.error("No valid reviews could be processed")
        return video_transcripts, "No valid reviews could be processed for this movie.", None

    try:
        length_options = PODCAST_LENGTH_OPTIONS.get(
            length_preference, PODCAST_LENGTH_OPTIONS[DEFAULT_LENGTH_PREFERENCE])
        final_summary_length_instruction = length_options["prompt_instruction"]
    except KeyError:
        logger.error(
            f"Invalid length_preference '{length_preference}' for final summary. Using default instruction.")
        final_summary_length_instruction = PODCAST_LENGTH_OPTIONS[
            DEFAULT_LENGTH_PREFERENCE]["prompt_instruction"]

    logger.info(
        f'Generating final summary with target length: "{final_summary_length_instruction}"')
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
    review_blob.upload_from_string(
        review_pickle_bytes, content_type='application/octet-stream')
    transcripts_blob.upload_from_string(
        transcripts_pickle_bytes, content_type='application/octet-stream')
    logger.info(
        f"Successfully saved results for '{movie}'{cache_log_suffix} to GCS.")
    logger.info(
        f"Time taken for '{movie}': {(time.time() - start_time):.2f} seconds")
    return video_transcripts, review, podcast_bytes


@st.cache_data(hash_funcs={bool: lambda x: f"spoiler_{x}"})
def generate_podcast(movie_title, allow_spoilers=False, length_preference: str = DEFAULT_LENGTH_PREFERENCE):
    video_transcripts, review, podcast_bytes = main(
        movie_title,
        allow_spoilers=allow_spoilers,
        length_preference=length_preference
    )
    return video_transcripts, review, podcast_bytes

def render_header():
    st.markdown(
        """
        <style>
        .header-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 1.5rem;
            margin-bottom: 2rem;
        }
        .logo-text {
            font-size: 28px;
            font-weight: 700;
            color: white;
        }
        .nav-links a {
            margin-left: 1.2rem;
            font-size: 16px;
            color: white;
            text-decoration: none;
        }
        .nav-links a:hover {
            text-decoration: underline;
        }
        </style>
        <div class="header-container">
            <div class="logo-text">🎬 CineCast <span style="font-weight:300;">AI</span></div>
            <div class="nav-links">
                <a href="#">Home</a>
                <a href="#">Podcasts</a>
                <a href="#">About</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    st.set_page_config(page_title="CineCast AI", page_icon="🎬")
    render_header()

    # ─── Custom Dark-Card Styles ───
    st.markdown(
        """
        <style>
        body, .stApp {
            background-color: #1c1c1c;
            color: #f5f5f5;
            font-family: 'Courier New', monospace;
        }

        .centered-container {
            max-width: 620px;
            margin-left: auto;
            margin-right: auto;
        }

        div.stForm {
            background-color: #2e2e2e;
            border: 2px dashed #888;
            border-radius: 0;
            padding: 24px;
        }

        div.stForm input, div.stForm .stTextInput>div>input {
            background-color: #000 !important;
            color: #fff !important;
            border: 2px solid #fff;
        }

        div.stForm .stCheckbox>label {
            color: #ccc !important;
            font-weight: bold;
        }

        div.stForm button[kind="primary"] {
            background-color: #000 !important;
            color: #fff !important;
            border: 2px solid #fff !important;
            font-weight: bold !important;
            text-transform: uppercase;
        }

        .movie-card {
            border: 2px dashed #888;
            border-radius: 0px;
            padding: 20px;
            margin: 30px auto;
            display: flex;
            gap: 25px;
            align-items: flex-start;
            background: #2e2e2e;
            font-family: 'Courier New', monospace;
            width: 620px;
            max-width: 100%;
        }

        .poster-container {
            flex-shrink: 0;
            border: 2px solid #aaa;
        }

        .movie-poster {
            width: 200px;
            height: auto;
            display: block;
        }

        .movie-info h1, .movie-info h3, .movie-summary {
            color: #f5f5f5;
        }

        [data-testid="stSidebar"] {
            background-color: #2e2e2e;
            border-right: 3px solid #888;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ─── Generate Podcast Card ───
    with st.container():
        st.markdown('<div class="centered-container">', unsafe_allow_html=True)
        with st.form(key="search_form"):
            st.markdown("## Generate Your Movie Podcast", unsafe_allow_html=True)

            # Movie title
            movie_title = st.text_input(
                label="Movie Title",
                placeholder="e.g. Silence of the Lambs",
                key="movie_title_input"
            )

            # Spoiler-free toggle (unique key)
            spoiler_free = st.checkbox(
                label="Spoiler-Free Mode",
                value=st.session_state.get("allow_spoilers", False),
                key="spoiler_toggle_form",
                help="Enable this to avoid plot spoilers"
            )

            # Length selector (unique key)
            length_label = st.selectbox(
                label="Episode Length",
                options=[PODCAST_LENGTH_OPTIONS[k]["ui_label"] for k in LENGTH_PREFERENCE_ORDER],
                index=LENGTH_PREFERENCE_ORDER.index(
                    st.session_state.get("length_preference", DEFAULT_LENGTH_PREFERENCE)
                ),
                key="length_label_form"
            )

            # Submit button
            generate_btn = st.form_submit_button(
                label="Generate Podcast",
                use_container_width=True
            )

        st.markdown('</div>', unsafe_allow_html=True)

        # ─── Handle form submission ───
        if generate_btn:
            # persist into session_state for your main() logic
            st.session_state.allow_spoilers = spoiler_free
            chosen_key = next(
                k for k, v in PODCAST_LENGTH_OPTIONS.items()
                if v["ui_label"] == length_label
            )
            st.session_state.length_preference = chosen_key

            if not movie_title:
                st.warning("Please enter a movie title first!")
            else:
                with st.spinner(
                    f"Searching for reviews and generating "
                    f"{'spoiler-free ' if spoiler_free else ''}"
                    f"podcast for '{movie_title}', may take up to 3 minutes..."
                ):
                    video_transcripts, review, podcast_bytes = generate_podcast(
                        movie_title,
                        allow_spoilers=spoiler_free,
                        length_preference=chosen_key
                    )
                
                # Retrieve movie metadata
                found_flag, movie_details = find_similar_movie_imdb(movie_title)

                if found_flag:
                    formatted_title = f"{movie_details['title']} ({movie_details['release_date']})"
                    director = movie_details.get('director', "Unknown")
                    description = movie_details.get('description', "No description available.")

                    # Display movie info card
                    st.markdown(f"""
                        <div class="movie-card">
                            <div class="poster-container">
                                <img src="{movie_details['poster']}" class="movie-poster">
                            </div>
                            <div class="movie-info">
                                <h1>{formatted_title}</h1>
                                <h3>Directed by: {director}</h3>
                                <p class="movie-summary">Summary: {description}</p>
                            </div>
                        </div>

                        <style>
                            .movie-card {{
                                border: 1px solid #2e2e2e;
                                border-radius: 15px;
                                padding: 20px;
                                margin: 30px auto;
                                display: flex;
                                gap: 25px;
                                align-items: flex-start;
                                background: #2e2e2e;;
                                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                                width: 620px;
                                max-width: 100%;
                            }}

                            .poster-container {{
                                flex-shrink: 0;
                                border-radius: 8px;
                                overflow: hidden;
                                border: 1px solid #444;
                            }}

                            .movie-poster {{
                                width: 200px;
                                height: auto;
                                display: block;
                            }}

                            .movie-info h1 {{
                                margin: 0 0 8px 0;
                                color: #fff;
                                font-size: 28px;
                            }}

                            .movie-info h3 {{
                                margin: 0 0 12px 0;
                                color: #fff;
                                font-size: 18px;
                            }}

                            .movie-summary {{
                                margin: 4px 0;
                                color: #d1d5db;
                                font-size: 16px;
                            }}
                        </style>
                    """, unsafe_allow_html=True)
                else:
                    st.info("Movie poster and summary unavailable.")

                st.subheader(f"Podcast for '{movie_title}' generated!")
                st.audio(podcast_bytes, format="audio/mp3")

                if "recent_episodes" not in st.session_state:
                    st.session_state.recent_episodes = []
                # Save recent episode
                new_episode = {
                    "title": movie_title,
                    "length": PODCAST_LENGTH_OPTIONS[chosen_key]["ui_label"],
                    "has_spoilers": not spoiler_free,   # <-- Fix here
                    "timestamp": time.strftime("%B %d, %Y")
                }
                st.session_state.recent_episodes.insert(0, new_episode)
                st.session_state.recent_episodes = st.session_state.recent_episodes[:3]

                # Download button
                spoiler_tag = "with_spoilers" if spoiler_free else "spoiler_free"
                fname = f"{movie_title.replace(' ', '_')}_{spoiler_tag}_{chosen_key}.mp3"
                st.download_button(
                    label="Download Podcast",
                    data=podcast_bytes,
                    file_name=fname,
                    mime="audio/mp3",
                )

                # Transcript expander
                with st.expander("Podcast Transcript"):
                    st.write(review)

                # Source Videos expander
                with st.expander("Source Videos"):
                    video_review_data = []
                    for info in video_transcripts:
                        tag = ("🚨 Contains Spoilers" 
                            if info.get("likely_has_spoilers", False) 
                            else "✅ Spoiler-Free")
                        link = f"[{info['title']} by {info['creator']}]({info['url']}) - {tag}"
                        video_review_data.append({"Reviews": link})
                    df = pd.DataFrame(video_review_data)
                    st.markdown(df.to_markdown(index=False), unsafe_allow_html=True)

        # ─── Recent Episodes Section ───
        if "recent_episodes" in st.session_state and st.session_state.recent_episodes:
            st.markdown("## 🎧 Recent Episodes")

            for episode in reversed(st.session_state.recent_episodes):
                title_display = f"🎬 {episode['title']}"
                meta_info = (
                    f"Length: {episode['length']}  |  "
                    f"{'✅ Spoiler-Free' if not episode.get('has_spoilers', False) else '🚨 Includes Spoilers'}  |  "
                    f"Generated on {episode['timestamp']}"
                )
                st.markdown(
                    f"""
                    <div style="background-color: #2e2e2e; padding: 15px 20px; border-radius: 12px; margin-bottom: 15px;">
                        <p style="color: #F9FAFB; margin: 0 0 6px 0;">{title_display}</p>
                        <p style="color: #D1D5DB; margin: 0;">{meta_info}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("---")
    st.caption(
        "Created by: Andrea Quiroz, Nihal Karim, Peeyush Patel, Sang Ahn, Suhho Lee"
    )
