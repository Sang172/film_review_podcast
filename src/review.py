import logging
import asyncio
from src.utils import get_gemini_response

logger = logging.getLogger(__name__)


async def get_review_summary(chunk, movie, allow_spoilers=False):
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
    summary = await get_gemini_response(prompt)
    return summary


async def review_summary_with_retry(chunk, movie, max_retries=20, initial_delay=5, allow_spoilers=False):

    retries = 0
    delay = initial_delay
    while retries <= max_retries:
        try:
            return await get_review_summary(chunk, movie, allow_spoilers=allow_spoilers)
        except Exception as e:
            logger.info(f"Error processing chunk '{chunk.get('title', 'Unknown')}' (Retry {retries + 1}/{max_retries}): {e}")
            if retries < max_retries:
                logger.info(f"Waiting {delay} seconds before retrying...")
                await asyncio.sleep(delay)
                delay *= 1
                retries += 1
            else:
                logger.error(f"Max retries reached for chunk '{chunk.get('title', 'Unknown')}'. Skipping. Error: {e}")
                return ""
            

async def _review_summary_parallel_with_retry(chunks, movie, allow_spoilers=False):

    tasks = []

    for chunk in chunks:
        task = asyncio.create_task(review_summary_with_retry(chunk, movie, allow_spoilers=allow_spoilers))
        tasks.append(task)

    results = await asyncio.gather(*tasks)

    return results

def review_summary_parallel_with_retry(chunks, movie, allow_spoilers=False):
    results = asyncio.run(_review_summary_parallel_with_retry(chunks=chunks, movie=movie, allow_spoilers=allow_spoilers))
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
    review = asyncio.run(get_gemini_response(prompt))
    return review