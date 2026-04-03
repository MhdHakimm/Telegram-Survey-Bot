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
        msg += (
            f"📋 There are *{len(surveys)}* active survey(s).\n\nUse /surveys to start."
        )
    else:
        msg += "😔 No active surveys right now."

    if is_admin:
        msg += "\n\n🔧 Admin access enabled. Use /admin"

    await update.effective_chat.send_message(msg, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS

    text = (
        "📖 *Commands*\n\n"
        "/start — Welcome\n"
        "/surveys — Take surveys\n"
        "/help — Help\n"
        "/cancel — Cancel\n"
    )

    if is_admin:
        text += "\n🔧 /admin — Admin panel"

    await update.effective_chat.send_message(text, parse_mode="Markdown")


def get_common_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("help", help_command),
    ]
