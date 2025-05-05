import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai
# from google.oauth2.service_account import Credentials

load_dotenv()

# credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
# credentials = Credentials.from_service_account_file(credentials_path)

def setup_logging():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    return logging.getLogger(__name__)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

proxy = os.environ.get('PROXY_ADDRESS')
# proxy = None

llm = genai.GenerativeModel("gemini-2.0-flash")
GCS_BUCKET_NAME = 'msds603_film_podcast'


# Podcast Length Configuration
PODCAST_LENGTH_OPTIONS = {
    "Clip": {
        "prompt_instruction": "under 500 words",
        "ui_label": "Clip (~3 min)",
        "help_text": "A quick glimpse — perfect for when you're short on time.",
        "filename_suffix": "_clip"
    },
    "Reel": {
        "prompt_instruction": "between 700 and 1100 words",
        "ui_label": "Reel (~7 min)",
        "help_text": "A fast-paced review you can enjoy with your coffee.",
        "filename_suffix": "_reel"
    },
    "Feature": {
        "prompt_instruction": "between 1500 and 2000 words", # Current default
        "ui_label": "Feature (~12 min) - Default",
        "help_text": "The full movie experience — detailed, thoughtful, and complete.",
        "filename_suffix": "" # No suffix for default to match existing cache
    }
    # "Epic": { Temporarily disabled due to length instructions not being followed
    #     "prompt_instruction": "between 2500 and 3500 words",
    #     "ui_label": "Epic (~20 min)",
    #     "help_text": "A deep dive into the film’s world, characters, and craft.",
    #     "filename_suffix": "_epic"
    # },
    # "Saga": {
    #     "prompt_instruction": "between 4500 and 5000 words",
    #     "ui_label": "Saga (~30 min)",
    #     "help_text": "An extended journey through every corner of the movie’s universe.",
    #     "filename_suffix": "_saga"
    # }
}
# Order for UI display
LENGTH_PREFERENCE_ORDER = ["Clip", "Reel", "Feature"] # "Epic", "Saga"]
# Default selection key
DEFAULT_LENGTH_PREFERENCE = "Feature"
