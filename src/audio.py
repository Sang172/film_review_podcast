import io
import logging
from google.cloud import texttospeech_v1beta1 as texttospeech
from pydub import AudioSegment

logger = logging.getLogger(__name__)

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