import os
from dotenv import load_dotenv

from supabase import create_client

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
            "meta": q.get("meta", {}) or {},
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


# ── Send Question (callback) ───────────────────────────
async def _send_question(query, context):
    questions = context.user_data["questions"]
    idx = context.user_data["index"]

    if idx >= len(questions):
        return True

    q = questions[idx]
    text = f"*Question {idx+1}/{len(questions)}*\n\n{q['text']}"

    # # IMAGE
    # if q["type"] == "image" and q["meta"].get("image_url"):
    #     await query.message.reply_photo(q["meta"]["image_url"])

    # MCQ
    if q["type"] == "mcq":
        await query.edit_message_text(
            text,
            reply_markup=_mcq_kb(idx, q["options"]),
            parse_mode="Markdown",
        )

    # LIKERT
    elif q["type"] == "likert":
        scale = q["meta"].get("scale", 5)

        buttons = [
            InlineKeyboardButton(str(i + 1), callback_data=f"ans_{idx}_{i}")
            for i in range(scale)
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([buttons]),
            parse_mode="Markdown",
        )

    # TEXT
    elif q["type"] == "text":
        await query.edit_message_text(
            text + "\n\n(Type your answer)",
            parse_mode="Markdown",
        )

    # RANKING
    elif q["type"] == "ranking":
        num = q["meta"].get("num_items", 3)
        await query.edit_message_text(
            text + f"\n\n(Enter {num} items separated by commas)",
            parse_mode="Markdown",
        )

    return False


# ── Send Question (message) ────────────────────────────
async def _send_question_message(update, context):
    questions = context.user_data["questions"]
    idx = context.user_data["index"]

    if idx >= len(questions):
        return True

    q = questions[idx]
    text = f"*Question {idx+1}/{len(questions)}*\n\n{q['text']}"

    if q["type"] == "mcq":
        await update.message.reply_text(
            text,
            reply_markup=_mcq_kb(idx, q["options"]),
            parse_mode="Markdown",
        )

    elif q["type"] == "likert":
        scale = q["meta"].get("scale", 5)

        buttons = [
            InlineKeyboardButton(str(i + 1), callback_data=f"ans_{idx}_{i}")
            for i in range(scale)
        ]

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup([buttons]),
            parse_mode="Markdown",
        )

    elif q["type"] == "text":
        await update.message.reply_text(
            text + "\n\n(Type your answer)",
            parse_mode="Markdown",
        )

    elif q["type"] == "ranking":
        num = q["meta"].get("num_items", 3)
        await update.message.reply_text(
            text + f"\n\n(Enter {num} items separated by commas)",
            parse_mode="Markdown",
        )

    return False


# ── TEXT ANSWER ───────────────────────────────────────
async def text_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data["index"]
    q = context.user_data["questions"][idx]

    user_text = update.message.text

    context.user_data["responses"].append(
        {
            "question_id": q["id"],
            "answer_text": user_text,
        }
    )

    # skip logic
    skip_to = q["meta"].get("skip_to")

    if skip_to:
        context.user_data["index"] = skip_to - 1
    else:
        context.user_data["index"] += 1

    done = await _send_question_message(update, context)

    if done:
        await _finish_survey(update, context)
        return ConversationHandler.END

    return ANSWERING


# ── BUTTON ANSWER ─────────────────────────────────────
async def answering_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = context.user_data["index"]
    q = context.user_data["questions"][idx]
    data = query.data

    if q["type"] == "mcq":
        option_id = int(data.split("_")[-1])
        context.user_data["responses"].append(
            {
                "question_id": q["id"],
                "option_id": option_id,
            }
        )

    elif q["type"] == "likert":
        score = int(data.split("_")[-1]) + 1
        context.user_data["responses"].append(
            {
                "question_id": q["id"],
                "numeric_value": score,
            }
        )

    # skip logic
    skip_to = q["meta"].get("skip_to")

    if skip_to:
        context.user_data["index"] = skip_to - 1
    else:
        context.user_data["index"] += 1

    done = await _send_question(query, context)

    if done:
        await _finish_survey(query, context)
        return ConversationHandler.END

    return ANSWERING


# ── Finish ────────────────────────────────────────────
async def _finish_survey(update_or_query, context):
    # ✅ HANDLE BOTH update + callback_query
    if hasattr(update_or_query, "effective_user"):
        user = update_or_query.effective_user
        chat = update_or_query.effective_chat
    else:
        user = update_or_query.from_user
        chat = update_or_query.message.chat

    user_id = user.id

    # ensure user exists
    supabase.table("user").upsert({"id": user_id, "username": user.username}).execute()

    # create survey response
    res = (
        supabase.table("survey_response")
        .insert(
            {
                "survey_id": context.user_data["survey_id"],
                "user_id": user_id,
            }
        )
        .execute()
    )

    survey_response_id = res.data[0]["id"]

    # save answers
    for r in context.user_data["responses"]:
        supabase.table("response").insert(
            {
                "survey_response_id": survey_response_id,
                "question_id": r["question_id"],
                "answer_text": r.get("answer_text"),
                "option_id": r.get("option_id"),
                "numeric_value": r.get("numeric_value"),
            }
        ).execute()

    # ✅ USE chat instead of effective_chat
    await chat.send_message("🎉 Survey completed!")


# ── Entry ─────────────────────────────────────────────
async def surveys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    surveys = get_surveys()

    if not surveys:
        await update.message.reply_text("No surveys available.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Select a survey:",
        reply_markup=_surveys_kb(surveys),
    )

    return SELECT_SURVEY


async def select_survey_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    survey_id = int(query.data.split("_")[1])
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


async def confirm_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

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
