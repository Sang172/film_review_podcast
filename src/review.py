import concurrent.futures
import time
import logging
from src.utils import get_gemini_response

logger = logging.getLogger(__name__)

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