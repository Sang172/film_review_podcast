from youtube_search import YoutubeSearch
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv
import os
import google.generativeai as genai
from google.cloud import texttospeech_v1beta1 as texttospeech
# from google.oauth2.service_account import Credentials
import concurrent.futures
import time
from pydub import AudioSegment
import logging
import streamlit as st
from gtts import gTTS
import pandas as pd
import io


load_dotenv()
# credentials_path=os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
# credentials = Credentials.from_service_account_file(credentials_path)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
proxy = os.environ.get('PROXY_ADDRESS')

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

llm = genai.GenerativeModel("gemini-2.0-flash")


def get_gemini_response(prompt):
    return llm.generate_content(prompt).text.strip()


def get_video_transcripts(videos, movie, proxy=proxy):

    video_transcripts = []
    proxies = {'http': proxy, 'https': proxy}

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

        if response.lower()=='yes':

            logger.info(f"Processing '{video_title}' by '{video_creator}'")

            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'], proxies=proxies)

                full_transcript = " ".join([item['text'] for item in transcript_list])

                video_transcripts.append({
                    'title': video_title,
                    'creator': video_creator,
                    'url': video_url,
                    'transcript': full_transcript
                })
                logger.info("Transcript Retrieved")
            except Exception as e:
                logger.error(f"{e}")
                logger.info("Transcript Not Found")

    return video_transcripts


def get_review_summary(chunk):
    video = f"review '{chunk['title']}' by '{chunk['creator']}'\n\n{chunk['transcript']}"
    logger.info('summarizing '+video.split('\n\n')[0])
    prompt = f"""
    You are an intelligent film critic.
    Your task is to write a summary of another person's film review.
    The summary should be around 1000 words.
    I will provide the film review below:
    {video}
    """
    podcast_transcript = get_gemini_response(prompt)
    return podcast_transcript

def review_summary_with_retry(chunk, max_retries=10, initial_delay=5):

    retries = 0
    delay = initial_delay
    while retries <= max_retries:
        try:
            return get_review_summary(chunk)
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
            

def review_summary_parallel_with_retry(chunks, max_workers=5):

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_chunk = {executor.submit(review_summary_with_retry, chunk): chunk for chunk in chunks}
        for future in concurrent.futures.as_completed(future_to_chunk):
            chunk = future_to_chunk[future]
            try:
                result = future.result()
                results.append(result)
            except:
                pass

    return results



def get_final_summary(chunks):
    combined_reviews = '\n\n----------------------\n\n'.join(chunks)
    prompt = f"""
    You are an intelligent film critic. Your task is to write a film review.
    I will give you multiple reviews about the same movie, each by a different person.
    Combine the information in the reviews to produce a single summary review that offers the most comprehensive overview.
    The summary review should be between 1500-2000 words in length.
    It should be written in essay format with no title where each paragraph is separated with newline separators. Do NOT include any bullet points.
    Dive into the summary review right away and do NOT include any introductory remarks such as "After going through the reviews".
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


def main(movie: str):
    search_term = movie + ' movie review'
    max_results = 5
    logger.info(f'Searching YouTube for reviews on {movie}...')
    videos = YoutubeSearch(search_term, max_results=max_results).to_dict()
    logger.info('Search complete, retrieving transcripts...')
    video_transcripts = get_video_transcripts(videos, movie)
    logger.info('Retrieval complete, analyzing reviews...')
    reviews = review_summary_parallel_with_retry(video_transcripts)
    review = get_final_summary(reviews)
    logger.info('Analysis complete, generating podcast...')
    podcast_bytes = create_podcast(review)
    logger.info(f"Podcast generation complete")
    return video_transcripts, review, podcast_bytes


@st.cache_data
def generate_podcast(movie_title):
    video_transcripts, review, podcast_bytes = main(movie_title)
    return video_transcripts, review, podcast_bytes


if __name__ == "__main__":
    st.title("CineCast AI")
    movie_title = st.text_input("Enter the movie title:")

    if movie_title:
        with st.spinner(f"Searching for reviews and generating podcast for '{movie_title}', may take up to 10 minutes..."):
            video_transcripts, review, podcast_bytes = generate_podcast(movie_title)

        st.subheader(f"Podcast for '{movie_title}' generated!")
        st.audio(podcast_bytes, format="audio/mp3")

        download_filename = f"{movie_title.replace(' ','_')}_podcast.mp3"
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
                title = video_info['title']
                creator = video_info['creator']
                url = video_info['url']
                markdown_link = f"[{title} by {creator}]({url})"
                video_review_data.append({"Reviews": markdown_link})

            df = pd.DataFrame(video_review_data)
            st.markdown(df.to_markdown(index=False), unsafe_allow_html=True)