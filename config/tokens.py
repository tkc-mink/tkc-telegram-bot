import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN_SHIBANOY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
