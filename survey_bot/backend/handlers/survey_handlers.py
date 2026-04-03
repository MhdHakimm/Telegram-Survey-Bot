import sys
import os

from supabase import create_client
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# ── Setup ─────────────────────────────────────────────
load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)

SELECT_SURVEY, CONFIRM_START, ANSWERING = range(3)


# ── DB Helpers ────────────────────────────────────────
def get_surveys():
    res = supabase.table("survey").select("id, title").execute()
    return res.data if res.data else []


def load_survey_from_db(survey_id):
    res = supabase.table("survey").select("*").eq("id", survey_id).execute()
    survey = res.data[0]

    q_res = (
        supabase.table("question")
        .select("*")
        .eq("survey_id", survey_id)
        .order("order_index")
        .execute()
    )

    questions = []

    for q in q_res.data:
        question = {
            "id": q["id"],
            "text": q["question_text"],
            "type": q["question_type"],
            "options": [],
        }

        if q["question_type"] == "mcq":
            opt_res = (
                supabase.table("option")
                .select("*")
                .eq("question_id", q["id"])
                .execute()
            )
            question["options"] = opt_res.data

        questions.append(question)

    return {"id": survey_id, "title": survey["title"], "questions": questions}


# ── Keyboards ─────────────────────────────────────────
def _surveys_kb(surveys):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(s["title"], callback_data=f"take_{s['id']}")]
            for s in surveys
        ]
    )


def _likert_kb(q_index):
    labels = ["1 😞", "2 🙁", "3 😐", "4 🙂", "5 😄"]
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(lbl, callback_data=f"ans_{q_index}_{i}")
                for i, lbl in enumerate(labels)
            ]
        ]
    )


def _mcq_kb(q_index, options):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    opt["option_text"], callback_data=f"ans_{q_index}_{opt['id']}"
                )
            ]
            for opt in options
        ]
    )


# ── Send Question (button) ────────────────────────────
async def _send_question(query, context):
    questions = context.user_data["questions"]
    idx = context.user_data["index"]

    if idx >= len(questions):
        return True

    q = questions[idx]
    text = f"*Question {idx+1}/{len(questions)}*\n\n{q['text']}"

    if q["type"] == "mcq":
        await query.edit_message_text(
            text, reply_markup=_mcq_kb(idx, q["options"]), parse_mode="Markdown"
        )

    elif q["type"] == "likert":
        await query.edit_message_text(
            text, reply_markup=_likert_kb(idx), parse_mode="Markdown"
        )

    elif q["type"] == "text":
        await query.edit_message_text(
            text + "\n\n(Type your answer)", parse_mode="Markdown"
        )

    return False


# ── Send Question (text) ──────────────────────────────
async def _send_question_message(update, context):
    questions = context.user_data["questions"]
    idx = context.user_data["index"]

    if idx >= len(questions):
        return True

    q = questions[idx]
    text = f"*Question {idx+1}/{len(questions)}*\n\n{q['text']}"

    if q["type"] == "mcq":
        await update.message.reply_text(
            text, reply_markup=_mcq_kb(idx, q["options"]), parse_mode="Markdown"
        )

    elif q["type"] == "likert":
        await update.message.reply_text(
            text, reply_markup=_likert_kb(idx), parse_mode="Markdown"
        )

    elif q["type"] == "text":
        await update.message.reply_text(
            text + "\n\n(Type your answer)", parse_mode="Markdown"
        )

    return False


# ── TEXT ANSWER ───────────────────────────────────────
async def text_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data["index"]
    q = context.user_data["questions"][idx]

    context.user_data["responses"].append(
        {"question_id": q["id"], "answer_text": update.message.text}
    )

    context.user_data["index"] += 1

    done = await _send_question_message(update, context)

    if done:
        await _finish_survey(update, context)
        return ConversationHandler.END

    return ANSWERING


# ── Finish (FIXED HERE) ───────────────────────────────
async def _finish_survey(update_or_query, context):
    user = update_or_query.effective_user
    user_id = user.id
    survey_id = context.user_data["survey_id"]
    responses = context.user_data["responses"]

    # 🔥 FIX: ensure user exists
    supabase.table("user").upsert({"id": user_id, "username": user.username}).execute()

    # create survey_response
    res = (
        supabase.table("survey_response")
        .insert({"survey_id": survey_id, "user_id": user_id})
        .execute()
    )

    if not res.data:
        await update_or_query.effective_chat.send_message("Error saving survey.")
        return

    survey_response_id = res.data[0]["id"]

    # save answers
    for r in responses:
        supabase.table("response").insert(
            {
                "survey_response_id": survey_response_id,
                "question_id": r["question_id"],
                "answer_text": r.get("answer_text"),
                "option_id": r.get("option_id"),
                "numeric_value": r.get("numeric_value"),
            }
        ).execute()

    await update_or_query.effective_chat.send_message("🎉 Survey completed!")


# ── Entry ─────────────────────────────────────────────
async def surveys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    surveys = get_surveys()

    if not surveys:
        await update.message.reply_text("No surveys available.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Select a survey:", reply_markup=_surveys_kb(surveys)
    )
    return SELECT_SURVEY


# ── Select Survey ─────────────────────────────────────
async def select_survey_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    survey_id = int(query.data.replace("take_", ""))
    survey = load_survey_from_db(survey_id)

    context.user_data.update(
        {
            "survey_id": survey_id,
            "questions": survey["questions"],
            "index": 0,
            "responses": [],
        }
    )

    await query.edit_message_text(
        f"{survey['title']}\n\nStart?",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Start", callback_data="start")]]
        ),
    )

    return CONFIRM_START


# ── Start ─────────────────────────────────────────────
async def confirm_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    done = await _send_question(query, context)

    if done:
        await _finish_survey(query, context)
        return ConversationHandler.END

    return ANSWERING


# ── Answering (buttons) ───────────────────────────────
async def answering_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = context.user_data["index"]
    q = context.user_data["questions"][idx]
    data = query.data

    if q["type"] == "mcq":
        option_id = int(data.split("_")[-1])
        context.user_data["responses"].append(
            {"question_id": q["id"], "option_id": option_id}
        )

    elif q["type"] == "likert":
        score = int(data.split("_")[-1]) + 1
        context.user_data["responses"].append(
            {"question_id": q["id"], "numeric_value": score}
        )

    context.user_data["index"] += 1

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
            ANSWERING: [
                CallbackQueryHandler(answering_cb),
                MessageHandler(filters.TEXT & ~filters.COMMAND, text_answer),
            ],
        },
        fallbacks=[],
    )
