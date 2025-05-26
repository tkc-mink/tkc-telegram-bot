import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKENS = {
    "tkc_shibanoy_bot": os.getenv("BOT_TOKEN_TKC_SHIBANOY"),
    "giant_jiw_bot": os.getenv("BOT_TOKEN_GIANT_JIW"),
    "p_tyre_tkc_bot": os.getenv("BOT_TOKEN_P_TYRE"),
    "tex_speed_bot": os.getenv("BOT_TOKEN_TEX_SPEED"),
}

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
