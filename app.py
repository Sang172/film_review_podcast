from youtube_search import YoutubeSearch
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv
import os
import google.generativeai as genai
from google.cloud import storage
from google.cloud import texttospeech_v1beta1 as texttospeech
# from google.oauth2.service_account import Credentials
import concurrent.futures
import time
from pydub import AudioSegment
import logging
import streamlit as st
from gtts import gTTS
import pickle
import pandas as pd
import io


load_dotenv()
# credentials_path=os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
# credentials = Credentials.from_service_account_file(credentials_path)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
proxy = os.environ.get('PROXY_ADDRESS')
# proxy = None

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

llm = genai.GenerativeModel("gemini-2.0-flash")


def get_gemini_response(prompt):
    return llm.generate_content(prompt).text.strip()

def is_spoiler_review(title):
    """Determine if a review contains spoilers based on the title"""
    title_lower = title.lower()

    spoiler_keywords = [
        'spoiler', 'spoilers', 
        'ending explained', 'plot twist', 
        'reveals', 'full plot',
        'what happens', 'plot details',
        'everything you missed', 'breakdown',
        'all secrets', 'finale explained', 
        'ending', 'finale', 'secrets'
    ]
    
    non_spoiler_phrases = [
        'no spoiler', 'no spoilers', 
        'spoiler free', 'spoiler-free',
        'without spoilers', 'spoilerless',
        'spoiler alert: none', 'non-spoiler'
    ]
    
    for phrase in non_spoiler_phrases:
        if phrase in title_lower:
            return False
    
    for keyword in spoiler_keywords:
        if keyword in title_lower:
            return True
    
    if 'review' in title_lower and ('detailed' in title_lower or 'deep dive' in title_lower):
        return True
    
    return False


def get_video_transcripts(videos, movie, proxy=proxy, allow_spoilers=False):
    video_transcripts = []
    proxies = {'http': proxy, 'https': proxy} if proxy else None

    logger.info(f"Starting transcript retrieval with allow_spoilers={allow_spoilers}")

    for video in videos:
        video_id = video['id']
        video_title = video['title'].replace('|',',')
        video_creator = video['channel'].replace('|',',')
        video_url = 'https://youtube.com' + video['url_suffix']

        review_or_not = f"""
        I will give you the title of a YouTube video.
        Your task is to determine whether or not it is a review video about the film '{movie}'.
        Your answer should be only 'yes' or 'no'.
        If the video is a movie trailer, your response should be 'no'.
        If the video is from the press junket, your reponse should be 'no'.
        If unsure, respond with a 'yes'.
        The title is provided below:
        {video_title}
        """
        response = get_gemini_response(review_or_not)

        if response.lower() == 'yes':
            # Check if this is a spoiler review
            contains_spoiler = is_spoiler_review(video_title)
            logger.info(f"Video '{video_title}' contains_spoiler={contains_spoiler}, allow_spoilers={allow_spoilers}")
            
            # Only skip if it contains spoilers AND we don't want spoilers
            if contains_spoiler and not allow_spoilers:
                logger.info(f"Skipping potential spoiler review: '{video_title}'")
                continue
            
            # Log if we found a spoiler review and we want spoilers
            if contains_spoiler and allow_spoilers:
                logger.info(f"Found likely spoiler review: '{video_title}'")

            logger.info(f"Processing '{video_title}' by '{video_creator}'")

            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'], proxies=proxies)
                # transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])

                full_transcript = " ".join([item['text'] for item in transcript_list])

                video_transcripts.append({
                    'title': video_title,
                    'creator': video_creator,
                    'url': video_url,
                    'transcript': full_transcript,
                    'likely_has_spoilers': contains_spoiler if 'contains_spoiler' in locals() else False
                })
                logger.info("Transcript Retrieved")
            except Exception as e:
                logger.error(f"{e}")
                logger.info("Transcript Not Found")

    return video_transcripts


def get_review_summary(chunk, movie, allow_spoilers=False):
    video = f"review '{chunk['title']}' by '{chunk['creator']}'\n\n{chunk['transcript']}"
    logger.info('summarizing '+video.split('\n\n')[0])
    
    spoiler_instruction = ""
    if not allow_spoilers:
        spoiler_instruction = "IMPORTANT: Do not include any plot spoilers or key story revelations in your summary."
    
    prompt = f"""
    You are an intelligent film critic.
    Your task is to write a summary of someone's review of the film "{movie}".
    If the provided review is not a dedicated review of "{movie}", just return 'Not a "{movie}" review'.
    Otherwise, summarize the review into around 1000 words.
    {spoiler_instruction}
    I will provide the film review below:
    {video}
    """
    podcast_transcript = get_gemini_response(prompt)
    return podcast_transcript

def review_summary_with_retry(chunk, movie, max_retries=10, initial_delay=5, allow_spoilers=False):

    retries = 0
    delay = initial_delay
    while retries <= max_retries:
        try:
            return get_review_summary(chunk, movie, allow_spoilers=allow_spoilers)
        except:
            logger.info(f"Error processing chunk '{chunk.get('title', 'Unknown')}' (Retry {retries + 1}/{max_retries})")
            if retries < max_retries:
                logger.info(f"Waiting {delay} seconds before retrying...")
                time.sleep(delay)
                delay *= 2
                retries += 1
            else:
                logger.info(f"Max retries reached for chunk '{chunk.get('title', 'Unknown')}'. Skipping.")
                return None
            

def review_summary_parallel_with_retry(chunks, movie, max_workers=5, allow_spoilers=False):

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_chunk = {executor.submit(review_summary_with_retry, chunk, movie, allow_spoilers): chunk for chunk in chunks}
        for future in concurrent.futures.as_completed(future_to_chunk):
            chunk = future_to_chunk[future]
            try:
                result = future.result()
                results.append(result)
            except:
                pass

    return results



def get_final_summary(chunks, movie, allow_spoilers=False):
    combined_reviews = '\n\n----------------------\n\n'.join(chunks)
    spoiler_instruction = ""
    if not allow_spoilers:
        spoiler_instruction = "IMPORTANT: Do not include any plot spoilers or key story revelations in your summary."
    prompt = f"""
    You are an intelligent film critic. Your task is to write a film review.
    I will give you multiple different reviews about the film "{movie}".
    Combine the information in the reviews to produce a single summary review that offers the most comprehensive overview.
    If there is any review that is related to movies other than "{movie}", ignore that review.
    The summary review should be between 1500-2000 words in length.
    It should be written in essay format with no title where each paragraph is separated with newline separators. Do NOT include any bullet points.
    Dive into the summary review right away and do NOT include any introductory remarks such as "After going through the reviews".
    {spoiler_instruction}
    I will provide the source reviews here:
    {combined_reviews}
    """
    review = get_gemini_response(prompt)
    return review

def get_audio_chunk(text, language_code="en-US", voice_name="en-US-Chirp3-HD-Leda"):

    client = texttospeech.TextToSpeechClient()

    input_text = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voice_name
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        request={"input": input_text, "voice": voice, "audio_config": audio_config}
    )

    return response.audio_content


def create_podcast(review):
    review_split = [x for x in review.split('\n') if len(x)>2]
    audio_segments = []
    one_second_silence = AudioSegment.silent(duration=1000)

    for i, chunk in enumerate(review_split):
        tries = 0
        while tries<5:
            try:
                audio_content = get_audio_chunk(chunk)
                break
            except Exception as e:
                # logger.info(f"audio creation failed with error: {e}")
                tries += 1
                time.sleep(1)
        segment = AudioSegment.from_mp3(io.BytesIO(audio_content))
        audio_segments.append(segment)
        audio_segments.append(one_second_silence)
        logger.info(f'{i+1} th podcast chunk created...')

    combined_audio = AudioSegment.empty()

    for segment in audio_segments:
        combined_audio += segment

    audio_buffer = io.BytesIO()
    combined_audio.export(audio_buffer, format="mp3")
    audio_buffer.seek(0)

    return audio_buffer.read()


def main(movie: str, allow_spoilers: bool = False):
    if allow_spoilers:
        search_term = movie + ' movie spoiler review'
    else:
        search_term = movie + ' movie no spoiler review'
    max_results = 5
    
    gcs_bucket_name = 'suhholee-cinecast-bucket'
    directory_name = movie.lower().replace(' ', '_')
    spoiler_suffix = "_spoiler" if allow_spoilers else "_no_spoiler"
    podcast_gcs_path = f"{directory_name}/{directory_name}{spoiler_suffix}_podcast.mp3"
    review_gcs_path = f"{directory_name}/{directory_name}{spoiler_suffix}_review_text.pkl"
    transcripts_gcs_path = f"{directory_name}/{directory_name}{spoiler_suffix}_source_videos.pkl"

    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket_name)

    podcast_blob = bucket.blob(podcast_gcs_path)
    review_blob = bucket.blob(review_gcs_path)
    transcripts_blob = bucket.blob(transcripts_gcs_path)

    if podcast_blob.exists() and review_blob.exists() and transcripts_blob.exists():
        logger.info(f"Cache hit for '{movie}' (spoilers: {allow_spoilers})")
        podcast_bytes = podcast_blob.download_as_bytes()
        review_pickle_bytes = review_blob.download_as_bytes()
        transcripts_pickle_bytes = transcripts_blob.download_as_bytes()

        review = pickle.loads(review_pickle_bytes)
        video_transcripts = pickle.loads(transcripts_pickle_bytes)

        logger.info(f"Successfully loaded cached data for '{movie}' (spoilers: {allow_spoilers}) from GCS.")
        return video_transcripts, review, podcast_bytes

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
    
    review = get_final_summary(reviews, movie, allow_spoilers=allow_spoilers)
    logger.info('Analysis complete, generating podcast...')
    
    podcast_bytes = create_podcast(review)
    logger.info(f"Podcast generation complete")

    review_pickle_bytes = pickle.dumps(review)
    transcripts_pickle_bytes = pickle.dumps(video_transcripts)
            
    podcast_blob.upload_from_string(podcast_bytes, content_type='audio/mpeg')
    review_blob.upload_from_string(review_pickle_bytes, content_type='application/octet-stream')
    transcripts_blob.upload_from_string(transcripts_pickle_bytes, content_type='application/octet-stream')
    logger.info(f"Successfully saved results for '{movie}' (spoilers: {allow_spoilers}) to GCS.")
    return video_transcripts, review, podcast_bytes


@st.cache_data(hash_funcs={bool: lambda x: f"spoiler_{x}"})
def generate_podcast(movie_title, allow_spoilers=False):
    video_transcripts, review, podcast_bytes = main(movie_title, allow_spoilers=allow_spoilers)
    return video_transcripts, review, podcast_bytes


if __name__ == "__main__":
    st.title("CineCast AI")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        movie_title = st.text_input("Enter movie title:")

    with col2:
        allow_spoilers = st.toggle("Include Spoilers", value=False, 
                          help="Toggle ON to include plot details and spoilers in the review. Toggle OFF for a spoiler-free experience.")
        
        if allow_spoilers:
            st.caption("🚨 Spoiler mode: The review may reveal major plot points and twists")
        else:
            st.caption("✅ Spoiler-free mode: No major plot reveals")


    if movie_title:
        with st.spinner(f"Searching for reviews and generating {'' if allow_spoilers else 'spoiler-free '}podcast for '{movie_title}', may take up to 10 minutes..."):
            video_transcripts, review, podcast_bytes = generate_podcast(movie_title, allow_spoilers=allow_spoilers)

        st.subheader(f"Podcast for '{movie_title}' generated!")
        st.audio(podcast_bytes, format="audio/mp3")

        spoiler_info = "with_spoilers" if allow_spoilers else "spoiler_free"
        download_filename = f"{movie_title.replace(' ','_')}_{spoiler_info}_podcast.mp3"
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