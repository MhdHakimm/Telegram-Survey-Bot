import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Hardcoded admin Telegram user IDs (comma-separated in .env)
ADMIN_IDS = []
_admin_ids_str = os.getenv("ADMIN_IDS", "")
if _admin_ids_str:
    ADMIN_IDS = [int(x.strip()) for x in _admin_ids_str.split(",") if x.strip()]

GOOGLE_CREDENTIALS_FILE = os.getenv(
    "GOOGLE_CREDENTIALS_FILE", "credentials/service_account.json"
)
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Survey Responses")
DATABASE_PATH = os.getenv("DATABASE_PATH", "survey_bot.db")
