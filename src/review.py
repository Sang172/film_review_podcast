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


def get_final_summary(chunks, movie, allow_spoilers=False, length_prompt_instruction: str = "between 1500 and 2000 words"):
    """
    Instead of returning a single‐voice essay, this will ask Gemini to produce
    a two-person dialogue between Jane and John, alternating turns and covering
    the key points extracted from the individual review summaries.
    """
    # 1) Filter and collect the raw summaries
    valid_chunks = [c for c in chunks if isinstance(c, str) and c.strip()]
    if not valid_chunks:
        logger.warning(f"No valid review summaries provided for final synthesis of '{movie}'.")
        return f"Could not generate a final summary for {movie} as no valid source review summaries were available."

    # 2) Turn each summary into a bullet point for clarity
    points = "\n".join(f"- {summary.strip()}" for summary in valid_chunks)

    # 3) Optional spoiler instruction
    spoiler_instruction = ""
    if not allow_spoilers:
        spoiler_instruction = "IMPORTANT: Do not include any plot spoilers or key story revelations in your discussion."

    # 4) Build the dialogue‐style prompt
    dialogue_prompt = f"""
    You’re writing a warm, engaging podcast script for CineCast AI, hosted by two friends, Jane and John. 
    They know each other well and speak like real people catching up over coffee—friendly, informal, and curious—but still informative and focused on the movie.

    **Tone & Style**  
    • Use contractions (“I’m”, “we’re”, “you’ll”) and occasional informal interjections (“mm-hmm”, “right?”, “you know?”).  
    • Have them ask each other quick follow-up questions (“John, what did you think of that?”, “Jane, did you catch that detail?”).  
    • Sprinkle in brief affirmations or reactions (“Absolutely!”, “Good point!”, “I was thinking the same”).  
    • Vary sentence length: mix short “checks” (“Sounds great.”) with slightly longer thoughts.  

    **Structure**  
    1. **Opening** (two lines):  
    - Jane greets the audience (“Hey everyone, welcome back to CineCast AI! I’m Jane.”)  
    - John responds (“And I’m John—excited to chat about {movie} today!”)  
    2. **Body**: alternate turns covering each of these **Key Points**, but don’t read them verbatim—**weave** them into the conversation naturally. After Jane’s first point, have her **ask** John a question about it.  
    3. **Closing** (two lines):  
    - John offers a final takeaway (“So, overall, {movie} is worth a watch because…”).  
    - Jane wraps up (“That’s our take—thanks for listening, and see you next time!”).

    **Key Points to Cover**  
    {points}

    **Length guideline:** {length_prompt_instruction}  

    Format like this, but let your copy *feel* like a chat, not a bullet list:

    Jane:  
    John:  
    Jane:  
    John:  
    …
    """

    # 5) Call Gemini and return the script
    review_dialogue = asyncio.run(get_gemini_response(dialogue_prompt))
    return review_dialogue.strip()