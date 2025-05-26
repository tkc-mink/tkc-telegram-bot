import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKENS = {
    "shibanoy": os.getenv("BOT_TOKEN_SHIBANOY"),
    "giantjiw": os.getenv("BOT_TOKEN_GIANTJIW"),
    "p_tyretkc": os.getenv("BOT_TOKEN_P_TYRETKC"),
    "tex_speed": os.getenv("BOT_TOKEN_TEX_SPEED"),
}

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
