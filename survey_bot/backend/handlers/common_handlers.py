import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

import database as db
from config import ADMIN_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin = user.id in ADMIN_IDS
    surveys = db.get_active_surveys()

    msg = f"👋 Hello, *{user.first_name}*! Welcome to the Survey Bot!\n\n"

    if surveys:
        msg += f"📋 There are *{len(surveys)}* active survey(s) available.\n\nUse /surveys to participate."
    else:
        msg += "😔 No active surveys right now. Check back soon!"

    if is_admin:
        msg += "\n\n🔧 You have *admin* access. Use /admin to manage surveys."

    await update.message.reply_text(msg, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS

    text = (
        "📖 *Available Commands*\n\n"
        "/start — Welcome message & survey count\n"
        "/surveys — Browse & take available surveys\n"
        "/help — Show this message\n"
        "/cancel — Cancel the current operation\n"
    )

    if is_admin:
        text += (
            "\n🔧 *Admin Commands*\n"
            "/admin — Open the admin panel\n"
        )

    await update.message.reply_text(text, parse_mode="Markdown")


def get_common_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("help", help_command),
    ]
