"""
Main entry point for the Survey Telegram Bot.

Run with:
    python bot.py
"""

import logging
import sys
import os

# Allow imports from backend/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram.ext import ApplicationBuilder

from config import BOT_TOKEN
import database as db
from handlers.common_handlers import get_common_handlers
from handlers.admin_handlers import get_admin_handler
from handlers.survey_handlers import get_survey_handler

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    # Initialise SQLite database
    db.init_db()
    logger.info("✅ Database initialised.")

    # Build the application
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register handlers — order matters:
    # ConversationHandlers must come before generic CommandHandlers
    app.add_handler(get_admin_handler())
    app.add_handler(get_survey_handler())
    for handler in get_common_handlers():
        app.add_handler(handler)

    logger.info("🤖 Bot is running. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
