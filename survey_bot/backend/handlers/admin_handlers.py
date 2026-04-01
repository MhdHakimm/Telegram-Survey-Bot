import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

SURVEY_DIR = "surveys"


def get_surveys():
    return [f for f in os.listdir(SURVEY_DIR) if f.endswith(".json")]


def load_survey(filename):
    with open(os.path.join(SURVEY_DIR, filename), "r") as f:
        return json.load(f)


# ── /admin ─────────────────────────────────────────────
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    surveys = get_surveys()

    if not surveys:
        await update.message.reply_text("No surveys found.")
        return

    buttons = [[InlineKeyboardButton(s, callback_data=f"sv_{s}")] for s in surveys]

    await update.message.reply_text(
        "Select a survey:", reply_markup=InlineKeyboardMarkup(buttons)
    )


# ── Select survey ──────────────────────────────────────
async def select_survey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    filename = query.data.replace("sv_", "")
    survey = load_survey(filename)

    context.user_data["active_survey"] = filename

    await query.edit_message_text(f"✅ Active Survey:\n\n{survey['title']}")


# ── Handler setup ──────────────────────────────────────
def get_admin_handler():
    return [
        CommandHandler("admin", admin_command),
        CallbackQueryHandler(select_survey, pattern="^sv_"),
    ]
