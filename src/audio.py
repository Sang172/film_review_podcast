import io
import logging
from google.cloud import texttospeech_v1beta1 as texttospeech
from pydub import AudioSegment
import asyncio

logger = logging.getLogger(__name__)

def _get_audio_chunk(text, language_code="en-US", voice_name="en-US-Chirp3-HD-Leda"):
    client = texttospeech.TextToSpeechClient()
    input_text = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code=language_code, name=voice_name)

    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    logger.info(f"Processing chunk '{text[:30]}'")
    response = client.synthesize_speech(request={"input": input_text, "voice": voice, "audio_config": audio_config})

    return response.audio_content


async def get_audio_chunk(text):
    response = await asyncio.to_thread(_get_audio_chunk, text)
    return response


async def get_audio_chunk_with_retry(text, initial_delay=5, max_retries=20):
    retries = 0
    delay = initial_delay
    while retries <= max_retries:
        try:
            return await get_audio_chunk(text)
        except Exception as e:
            logger.info(f"Error processing chunk '{text[:30]}' (Retry {retries + 1}/{max_retries}): {e}")
            if retries < max_retries:
                logger.info(f"Waiting {delay} seconds before retrying...")
                await asyncio.sleep(delay)
                delay *= 1
                retries += 1
            else:
                logger.error(f"Max retries reached for chunk '{text[:30]}'. Skipping. Error: {e}")
                return None


async def _create_podcast(review):
    review_split = [x for x in review.split('\n') if len(x)>2]
    tasks = []
    one_second_silence = AudioSegment.silent(duration=1000)

    for chunk in review_split:
        segment = asyncio.create_task(get_audio_chunk_with_retry(chunk))
        tasks.append(segment)

    audio_segments = await asyncio.gather(*tasks)

    combined_audio = AudioSegment.empty()

    for segment in audio_segments:
        if segment is not None:
            combined_audio += AudioSegment.from_mp3(io.BytesIO(segment))
            combined_audio += one_second_silence

    audio_buffer = io.BytesIO()
    combined_audio.export(audio_buffer, format="mp3")
    audio_buffer.seek(0)

    return audio_buffer.read()


def create_podcast(review):
    result = asyncio.run(_create_podcast(review))
    return result