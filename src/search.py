import logging
from youtube_transcript_api import YouTubeTranscriptApi
from src.config import proxy
from src.utils import get_gemini_response, is_spoiler_review

logger = logging.getLogger(__name__)

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
            contains_spoiler = is_spoiler_review(video_title)
            logger.info(f"Video '{video_title}' contains_spoiler={contains_spoiler}, allow_spoilers={allow_spoilers}")
            if contains_spoiler and not allow_spoilers:
                logger.info(f"Skipping potential spoiler review: '{video_title}'")
                continue
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