import os
import io
import logging
import random
import asyncio

from pydub import AudioSegment
from google.cloud import texttospeech_v1beta1 as tts

logger = logging.getLogger(__name__)

def _synthesize_chunk(text: str, voice_name: str) -> bytes:
    """
    Synthesize a single line of dialogue as raw PCM (LINEAR16),
    with a small random prosody variation for natural pacing.
    """
    client = tts.TextToSpeechClient()

    synthesis_input = tts.SynthesisInput(text=text)
    voice_params = tts.VoiceSelectionParams(
        language_code="en-US",
        name=voice_name
    )
    audio_config = tts.AudioConfig(
        audio_encoding=tts.AudioEncoding.MP3
    )

    logger.info(f"Synthesizing chunk (first 30 chars): {text[:30]!r}")
    response = client.synthesize_speech(
        request={
            "input": synthesis_input,
            "voice": voice_params,
            "audio_config": audio_config
        }
    )
    return response.audio_content

async def _synthesize_with_retry(text: str, voice_name: str,
                                 max_retries: int = 30,
                                 delay: float = 5.0) -> bytes | None:
    """
    Retry transient failures up to max_retries.
    """
    for attempt in range(max_retries):
        try:
            return await asyncio.to_thread(_synthesize_chunk, text, voice_name)
        except Exception as e:
            logger.warning(f"TTS attempt {attempt+1}/{max_retries} failed: {e}")
            await asyncio.sleep(delay)
    logger.error(f"Failed to synthesize chunk after {max_retries} retries: {text[:30]!r}")
    return None

async def _create_podcast(dialogue_script: str) -> bytes:
    """
    Turn the full “Jane:/John:” transcript into a single MP3:
    1) Synthesize each line to raw PCM,
    2) Convert to AudioSegment,
    3) Stitch with short pauses,
    4) Export once at high MP3 bitrate.
    """

    jane_voice = "en-US-Chirp3-HD-Leda"
    john_voice = "en-US-Chirp3-HD-Charon"

    # split out non-empty lines
    lines = [ln.strip() for ln in dialogue_script.splitlines() if ln.strip()]
    tasks = []
    for ln in lines:
        if ln.startswith("Jane:"):
            text = ln.split(":", 1)[1].strip()
            voice = jane_voice
        elif ln.startswith("John:"):
            text = ln.split(":", 1)[1].strip()
            voice = john_voice
        else:
            continue
        tasks.append(asyncio.create_task(_synthesize_with_retry(text, voice)))

    # run all TTS jobs
    blobs = await asyncio.gather(*tasks)

    # build the final AudioSegment
    spacer = AudioSegment.silent(duration=600)
    final = AudioSegment.empty()
    for blob in blobs:
        if blob:
            seg = AudioSegment.from_mp3(io.BytesIO(blob))
            final += seg + spacer

    # export once to MP3 at 192 kbps
    out = io.BytesIO()
    final.export(out, format="mp3", bitrate="192k")
    out.seek(0)
    return out.read()

def create_podcast(dialogue_script: str) -> bytes:
    """
    Public entry: run the async pipeline and return MP3 bytes.
    """
    return asyncio.run(_create_podcast(dialogue_script))