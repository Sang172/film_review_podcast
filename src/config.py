import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai
from google.oauth2.service_account import Credentials

load_dotenv()

credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
credentials = Credentials.from_service_account_file(credentials_path)

def setup_logging():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    return logging.getLogger(__name__)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# proxy = os.environ.get('PROXY_ADDRESS')
proxy = None

llm = genai.GenerativeModel("gemini-2.0-flash")
GCS_BUCKET_NAME = 'msds603_film_podcast'