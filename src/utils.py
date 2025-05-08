from src.config import llm
import asyncio
from imdb import IMDb


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


def find_similar_movie_imdb(query):
    ia = IMDb()
    try:
        movies = ia.search_movie(query)
        if not movies:
            return False, {}

        best_match = ia.get_movie(movies[0].movieID)
        ia.update(best_match, info=['main', 'release dates'])

        title = best_match.get('title')
        poster = best_match.get(
            'full-size cover url')
        release_date = best_match.get('year') if 'year' in best_match else None
        director_list = best_match.get('directors', [])
        director = ', '.join([d['name']
                             for d in director_list]) if director_list else None
        plots = best_match.get('plot')
        description = plots[0] if plots else best_match.get('plot outline')
        if description and isinstance(description, str) and '::' in description:
            description = description.split('::')[0]  # Remove author credit
        return True, {
            'title': title,
            'poster': poster,
            'release_date': release_date,
            'director': director,
            'description': description
        }
    except Exception as e:
        print(f"IMDb Error: {e}")
        return False, {}
