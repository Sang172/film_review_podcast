import logging
from youtube_transcript_api import YouTubeTranscriptApi
from src.config import proxy
from src.utils import get_gemini_response, is_spoiler_review
import asyncio

logger = logging.getLogger(__name__)


async def get_single_trasncript(video, movie, proxy=proxy, allow_spoilers=False):
    proxies = {'http': proxy, 'https': proxy} if proxy else None
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
    response = await get_gemini_response(review_or_not)

    if response.lower() == 'yes':
        contains_spoiler = is_spoiler_review(video_title)
        logger.info(f"Video '{video_title}' contains_spoiler={contains_spoiler}, allow_spoilers={allow_spoilers}")
        if contains_spoiler and not allow_spoilers:
            logger.info(f"Skipping potential spoiler review: '{video_title}' by '{video_creator}'")
            return None
        if contains_spoiler and allow_spoilers:
            logger.info(f"Found likely spoiler review: '{video_title}' by '{video_creator}'")


        try:
            transcript_list = await asyncio.to_thread(YouTubeTranscriptApi.get_transcript, video_id, languages=['en'], proxies=proxies)
            # transcript_list = await asyncio.to_thread(YouTubeTranscriptApi.get_transcript, video_id, languages=['en'])

            full_transcript = " ".join([item['text'] for item in transcript_list])

            logger.info(f"Transcript for '{video_title}' by '{video_creator}' Retrieved")

            return  {
                'title': video_title,
                'creator': video_creator,
                'url': video_url,
                'transcript': full_transcript,
                'likely_has_spoilers': contains_spoiler if 'contains_spoiler' in locals() else False
            }
        except Exception as e:
            logger.error(f"{e}")
            logger.info(f"Transcript for '{video_title}' by '{video_creator}' not found")
            return None


async def _get_video_transcripts(videos, movie, proxy=proxy, allow_spoilers=False):
    
    logger.info(f"Starting transcript retrieval with allow_spoilers={allow_spoilers}")

    tasks = []

    for video in videos:
        segment = asyncio.create_task(get_single_trasncript(video, movie, proxy=proxy, allow_spoilers=allow_spoilers))
        tasks.append(segment)

    video_transcripts = await asyncio.gather(*tasks)

    return video_transcripts

def get_video_transcripts(videos, movie, proxy=proxy, allow_spoilers=False):
    result = asyncio.run(_get_video_transcripts(videos, movie, proxy=proxy, allow_spoilers=allow_spoilers))
    result = [x for x in result if x is not None]
    return result