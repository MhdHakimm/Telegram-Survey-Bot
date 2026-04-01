import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
)

# ── Constants ─────────────────────────────────────────
SURVEY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "surveys"
)

SELECT_SURVEY, CONFIRM_START, ANSWERING = range(100, 103)


# ── Helpers ───────────────────────────────────────────
def get_surveys():
    return [f for f in os.listdir(SURVEY_DIR) if f.endswith(".json")]


def load_survey(filename):
    with open(os.path.join(SURVEY_DIR, filename), "r") as f:
        return json.load(f)


# ── Keyboards ─────────────────────────────────────────
def _surveys_kb(surveys):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(s["title"], callback_data=f"take_{s['file']}")]
            for s in surveys
        ]
    )


def _likert_kb(q_index: int):
    labels = ["1 😞", "2 🙁", "3 😐", "4 🙂", "5 😄"]
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(lbl, callback_data=f"ans_{q_index}_{i}")
                for i, lbl in enumerate(labels)
            ]
        ]
    )


def _mcq_kb(q_index: int, options):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(opt, callback_data=f"ans_{q_index}_{i}")]
            for i, opt in enumerate(options)
        ]
    )


# ── Send Question ─────────────────────────────────────
async def _send_question(query, context: ContextTypes.DEFAULT_TYPE):
    questions = context.user_data["sq_questions"]
    idx = context.user_data["sq_index"]

    if idx >= len(questions):
        return True

    q = questions[idx]
    total = len(questions)

    header = f"*Question {idx + 1} of {total}*\n\n{q['text']}"

    if q["type"] == "mcq":
        await query.edit_message_text(
            header,
            reply_markup=_mcq_kb(idx, q["options"]),
            parse_mode="Markdown",
        )

    elif q["type"] == "text":
        await query.edit_message_text(
            header + "\n\n(Type your answer)",
            parse_mode="Markdown",
        )

    elif q["type"] == "likert":
        await query.edit_message_text(
            header,
            reply_markup=_likert_kb(idx),
            parse_mode="Markdown",
        )

    return False


# ── Finish ────────────────────────────────────────────
async def _finish_survey(query, context: ContextTypes.DEFAULT_TYPE):
    responses = context.user_data["sq_responses"]

    await query.edit_message_text("🎉 Survey completed!")

    print("Responses:")
    print(responses)


# ── Entry ─────────────────────────────────────────────
async def surveys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = get_surveys()

    if not files:
        await update.message.reply_text("No surveys available.")
        return ConversationHandler.END

    surveys = [{"title": load_survey(f)["title"], "file": f} for f in files]

    await update.message.reply_text(
        "Select a survey:",
        reply_markup=_surveys_kb(surveys),
    )

    return SELECT_SURVEY


# ── Select Survey ─────────────────────────────────────
async def select_survey_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    filename = query.data.replace("take_", "")
    survey = load_survey(filename)

    context.user_data.update(
        {
            "sq_filename": filename,
            "sq_questions": survey["questions"],
            "sq_index": 0,
            "sq_responses": [],
        }
    )

    await query.edit_message_text(
        f"{survey['title']}\n\nStart?",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Start", callback_data="start_yes")]]
        ),
    )

    return CONFIRM_START


# ── Confirm Start ─────────────────────────────────────
async def confirm_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    done = await _send_question(query, context)

    if done:
        await _finish_survey(query, context)
        return ConversationHandler.END

    return ANSWERING


# ── Answering ─────────────────────────────────────────
async def answering_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    questions = context.user_data["sq_questions"]
    idx = context.user_data["sq_index"]
    question = questions[idx]

    # MCQ
    if question["type"] == "mcq":
        opt_index = int(data.split("_")[-1])
        selected = question["options"][opt_index]

        context.user_data["sq_responses"].append(
            {
                "question": question["text"],
                "answer": selected,
            }
        )

    # Likert
    elif question["type"] == "likert":
        score = int(data.split("_")[-1]) + 1

        context.user_data["sq_responses"].append(
            {
                "question": question["text"],
                "answer": score,
            }
        )

    context.user_data["sq_index"] += 1

    done = await _send_question(query, context)

    if done:
        await _finish_survey(query, context)
        return ConversationHandler.END

    return ANSWERING


# ── Handler ───────────────────────────────────────────
def get_survey_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("surveys", surveys_command)],
        states={
            SELECT_SURVEY: [CallbackQueryHandler(select_survey_cb)],
            CONFIRM_START: [CallbackQueryHandler(confirm_start_cb)],
            ANSWERING: [CallbackQueryHandler(answering_cb)],
        },
        fallbacks=[],
    )
