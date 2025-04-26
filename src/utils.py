from src.config import llm
import asyncio

async def get_gemini_response(prompt):
    response = await asyncio.to_thread(llm.generate_content, prompt)
    return response.text.strip()

def is_spoiler_review(title):
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