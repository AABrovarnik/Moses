import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID", "0")) if os.getenv("MANAGER_CHAT_ID") else None
DB_PATH = "bot_state.db"
