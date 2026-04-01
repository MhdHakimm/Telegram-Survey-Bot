# """
# Survey-taking conversation handler.
# Entry point: /surveys

# States
# ──────
# SELECT_SURVEY   — user sees active surveys and picks one
# CONFIRM_START   — user confirms they want to start
# ANSWERING       — question loop (Likert / MCQ / Ranking)

# After the final answer the responses are saved to Google Sheets
# and the conversation ends automatically.
# """

# import sys
# import os

# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# from telegram.ext import (
#     ContextTypes,
#     ConversationHandler,
#     CommandHandler,
#     CallbackQueryHandler,
# )

# import database as db
# from services.sheets_service import save_responses

# # Offset states so they never clash with admin states (0-16)
# SELECT_SURVEY, CONFIRM_START, ANSWERING = range(100, 103)


# # ── Keyboards ─────────────────────────────────────────────────────────────────


# def _surveys_kb(surveys):
#     return InlineKeyboardMarkup(
#         [
#             [InlineKeyboardButton(s["title"], callback_data=f"take_{s['id']}")]
#             for s in surveys
#         ]
#     )


# def _likert_kb(question_id: int):
#     labels = ["1\n😞", "2\n🙁", "3\n😐", "4\n🙂", "5\n😄"]
#     return InlineKeyboardMarkup(
#         [
#             [
#                 InlineKeyboardButton(lbl, callback_data=f"ans_{question_id}_{i + 1}")
#                 for i, lbl in enumerate(labels)
#             ]
#         ]
#     )


# def _mcq_kb(question_id: int, options):
#     return InlineKeyboardMarkup(
#         [
#             [
#                 InlineKeyboardButton(
#                     opt["option_text"],
#                     callback_data=f"ans_{question_id}_opt_{opt['id']}",
#                 )
#             ]
#             for opt in options
#         ]
#     )


# def _ranking_kb(question_id: int, remaining_options):
#     return InlineKeyboardMarkup(
#         [
#             [
#                 InlineKeyboardButton(
#                     opt["option_text"], callback_data=f"rank_{question_id}_{opt['id']}"
#                 )
#             ]
#             for opt in remaining_options
#         ]
#     )


# # ── Internal helpers ──────────────────────────────────────────────────────────


# async def _send_question(query, context: ContextTypes.DEFAULT_TYPE) -> bool:
#     """
#     Edit the current message to show the next question.
#     Returns True when all questions have been asked (survey complete).
#     """
#     questions = context.user_data["sq_questions"]
#     idx = context.user_data["sq_index"]

#     if idx >= len(questions):
#         return True  # done

#     q = questions[idx]
#     qtype = q["question_type"]
#     q_id = q["id"]
#     total = len(questions)

#     header = f"*Question {idx + 1} of {total}*\n\n{q['question_text']}"

#     if qtype == "likert":
#         body = "\n\n_Rate from 1 (Strongly Disagree) to 5 (Strongly Agree)_"
#         await query.edit_message_text(
#             header + body, reply_markup=_likert_kb(q_id), parse_mode="Markdown"
#         )

#     elif qtype == "multiple_choice":
#         options = db.get_options_by_question(q_id)
#         await query.edit_message_text(
#             header, reply_markup=_mcq_kb(q_id, options), parse_mode="Markdown"
#         )

#     elif qtype == "ranking":
#         options = db.get_options_by_question(q_id)
#         context.user_data["sq_rank_all"] = {
#             str(o["id"]): o["option_text"] for o in options
#         }
#         context.user_data["sq_rank_remaining"] = [dict(o) for o in options]
#         context.user_data["sq_rank_selected"] = []
#         body = "\n\n_Tap options in your preferred order (1st choice first)_"
#         await query.edit_message_text(
#             header + body,
#             reply_markup=_ranking_kb(q_id, options),
#             parse_mode="Markdown",
#         )

#     return False


# # async def _finish_survey(query, context: ContextTypes.DEFAULT_TYPE):
# #     """Save responses to Google Sheets and thank the user."""
# #     survey_id = context.user_data["sq_survey_id"]
# #     survey_title = context.user_data["sq_survey_title"]
# #     responses = context.user_data["sq_responses"]
# #     user = query.from_user

# #     try:
# #         save_responses(
# #             survey_id=survey_id,
# #             survey_title=survey_title,
# #             user_id=user.id,
# #             username=user.username,
# #             first_name=user.first_name,
# #             responses=responses,
# #         )
# #         db.mark_survey_completed(survey_id, user.id)
# #         await query.edit_message_text(
# #             "🎉 *Thank you for completing the survey!*\n\n"
# #             "Your responses have been saved. We really appreciate your time! 🙏\n\n"
# #             "Use /surveys to take another survey.",
# #             parse_mode="Markdown",
# #         )
# #     except Exception as exc:
# #         await query.edit_message_text(
# #             "✅ Survey completed!\n\n"
# #             f"⚠️ There was a problem saving your responses: `{exc}`\n"
# #             "Please let the admin know.",
# #             parse_mode="Markdown",
# #         )


# async def _finish_survey(query, context: ContextTypes.DEFAULT_TYPE):
#     survey_id = context.user_data["sq_survey_id"]
#     survey_title = context.user_data["sq_survey_title"]
#     responses = context.user_data["sq_responses"]
#     user = query.from_user

#     try:
#         # Save to SQLite
#         db.save_response(
#             survey_id=survey_id,
#             user_id=user.id,
#             username=user.username,
#             first_name=user.first_name,
#             responses=responses,
#         )

#         db.mark_survey_completed(survey_id, user.id)

#         await query.edit_message_text(
#             "🎉 *Thank you for completing the survey!*\n\n"
#             "Your responses have been saved. 🙏\n\n"
#             "Use /surveys to take another survey.",
#             parse_mode="Markdown",
#         )

#     except Exception as exc:
#         print("ERROR:", exc)

#         await query.edit_message_text(
#             " Error saving your responses.\n" "Please try again later.",
#         )


# # ── /surveys entry point ──────────────────────────────────────────────────────


# async def surveys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     surveys = db.get_active_surveys()
#     if not surveys:
#         await update.message.reply_text(
#             "😔 There are no active surveys right now.\nCheck back soon!"
#         )
#         return ConversationHandler.END

#     await update.message.reply_text(
#         "📋 *Available Surveys*\n\nSelect one to get started:",
#         reply_markup=_surveys_kb(surveys),
#         parse_mode="Markdown",
#     )
#     return SELECT_SURVEY


# # ── SELECT_SURVEY ─────────────────────────────────────────────────────────────


# async def select_survey_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()

#     survey_id = int(query.data.split("_")[-1])
#     user_id = update.effective_user.id

#     # Prevent duplicate submissions
#     if db.has_user_completed_survey(survey_id, user_id):
#         surveys = db.get_active_surveys()
#         await query.edit_message_text(
#             "✅ You have already completed this survey!\n\nChoose another:",
#             reply_markup=_surveys_kb(surveys),
#         )
#         return SELECT_SURVEY

#     survey = db.get_survey_by_id(survey_id)
#     questions = db.get_questions_by_survey(survey_id)

#     if not questions:
#         await query.edit_message_text(
#             "⚠️ This survey has no questions yet. Choose another:"
#         )
#         return SELECT_SURVEY

#     # Initialise session
#     context.user_data.update(
#         {
#             "sq_survey_id": survey_id,
#             "sq_survey_title": survey["title"],
#             "sq_questions": [dict(q) for q in questions],
#             "sq_index": 0,
#             "sq_responses": [],
#         }
#     )

#     desc = f"\n\n_{survey['description']}_" if survey["description"] else ""
#     await query.edit_message_text(
#         f"📋 *{survey['title']}*{desc}\n\n"
#         f"This survey has *{len(questions)}* question(s).\n\nReady to begin?",
#         reply_markup=InlineKeyboardMarkup(
#             [
#                 [
#                     InlineKeyboardButton(
#                         "✅ Let's Start!", callback_data="survey_start_yes"
#                     )
#                 ],
#                 [InlineKeyboardButton("❌ Not Now", callback_data="survey_start_no")],
#             ]
#         ),
#         parse_mode="Markdown",
#     )
#     return CONFIRM_START


# # ── CONFIRM_START ─────────────────────────────────────────────────────────────


# async def confirm_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()

#     if query.data == "survey_start_no":
#         surveys = db.get_active_surveys()
#         await query.edit_message_text(
#             "No problem! Here are the available surveys:",
#             reply_markup=_surveys_kb(surveys),
#         )
#         return SELECT_SURVEY

#     done = await _send_question(query, context)
#     if done:
#         await _finish_survey(query, context)
#         return ConversationHandler.END
#     return ANSWERING


# # ── ANSWERING ─────────────────────────────────────────────────────────────────


# async def answering_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()
#     data = query.data

#     questions = context.user_data["sq_questions"]
#     idx = context.user_data["sq_index"]
#     question = questions[idx]
#     qtype = question["question_type"]
#     q_id = question["id"]

#     # ── Likert answer ─────────────────────────────────────────────────────────
#     if qtype == "likert" and data.startswith(f"ans_{q_id}_"):
#         score = int(data.split("_")[-1])
#         labels = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
#         answer_text = f"{score} - {labels[score - 1]}"
#         context.user_data["sq_responses"].append(
#             {
#                 "question_num": idx + 1,
#                 "question_text": question["question_text"],
#                 "question_type": "likert",
#                 "answer": answer_text,
#             }
#         )
#         context.user_data["sq_index"] += 1
#         done = await _send_question(query, context)
#         if done:
#             await _finish_survey(query, context)
#             return ConversationHandler.END
#         return ANSWERING

#     # ── MCQ answer ────────────────────────────────────────────────────────────
#     if qtype == "multiple_choice" and data.startswith(f"ans_{q_id}_"):
#         opt_id = int(data.split("_")[-1])
#         options = db.get_options_by_question(q_id)
#         opt_map = {o["id"]: o["option_text"] for o in options}
#         answer_text = opt_map.get(opt_id, str(opt_id))
#         context.user_data["sq_responses"].append(
#             {
#                 "question_num": idx + 1,
#                 "question_text": question["question_text"],
#                 "question_type": "multiple_choice",
#                 "answer": answer_text,
#             }
#         )
#         context.user_data["sq_index"] += 1
#         done = await _send_question(query, context)
#         if done:
#             await _finish_survey(query, context)
#             return ConversationHandler.END
#         return ANSWERING

#     # ── Ranking answer (tap one by one) ───────────────────────────────────────
#     if qtype == "ranking" and data.startswith(f"rank_{q_id}_"):
#         opt_id = int(data.split("_")[-1])
#         rank_all = context.user_data["sq_rank_all"]
#         remaining = context.user_data["sq_rank_remaining"]
#         selected = context.user_data["sq_rank_selected"]

#         opt_text = rank_all[str(opt_id)]
#         selected.append(opt_text)
#         remaining = [o for o in remaining if o["id"] != opt_id]
#         context.user_data["sq_rank_remaining"] = remaining
#         context.user_data["sq_rank_selected"] = selected

#         if remaining:
#             rank_num = len(selected) + 1
#             ranked_so_far = "\n".join(f"{i + 1}. {o}" for i, o in enumerate(selected))
#             header = (
#                 f"*Question {idx + 1} of {len(questions)}*\n\n"
#                 f"{question['question_text']}\n\n"
#                 f"✅ *Ranked so far:*\n{ranked_so_far}\n\n"
#                 f"Now tap your *#{rank_num}* choice:"
#             )
#             await query.edit_message_text(
#                 header,
#                 reply_markup=_ranking_kb(q_id, remaining),
#                 parse_mode="Markdown",
#             )
#             return ANSWERING

#         # All options ranked
#         answer_text = " → ".join(f"{i + 1}. {o}" for i, o in enumerate(selected))
#         context.user_data["sq_responses"].append(
#             {
#                 "question_num": idx + 1,
#                 "question_text": question["question_text"],
#                 "question_type": "ranking",
#                 "answer": answer_text,
#             }
#         )
#         context.user_data["sq_index"] += 1
#         done = await _send_question(query, context)
#         if done:
#             await _finish_survey(query, context)
#             return ConversationHandler.END
#         return ANSWERING

#     return ANSWERING


# # ── Cancel ────────────────────────────────────────────────────────────────────


# async def cancel_survey(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await update.message.reply_text("Survey cancelled. Use /surveys to start again.")
#     return ConversationHandler.END


# # ── Build handler ─────────────────────────────────────────────────────────────


# def get_survey_handler() -> ConversationHandler:
#     return ConversationHandler(
#         entry_points=[CommandHandler("surveys", surveys_command)],
#         states={
#             SELECT_SURVEY: [
#                 CallbackQueryHandler(select_survey_cb, pattern=r"^take_\d+$"),
#             ],
#             CONFIRM_START: [
#                 CallbackQueryHandler(confirm_start_cb, pattern=r"^survey_start_"),
#             ],
#             ANSWERING: [
#                 CallbackQueryHandler(answering_cb, pattern=r"^(ans_|rank_)"),
#             ],
#         },
#         fallbacks=[CommandHandler("cancel", cancel_survey)],
#         allow_reentry=True,
#         name="survey_conversation",
#     )


import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
)

import database as db

SELECT_SURVEY, CONFIRM_START, ANSWERING = range(100, 103)


# ── Keyboards ─────────────────────────────────────────────────────────────────


def _surveys_kb(surveys):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(s["title"], callback_data=f"take_{s['id']}")]
            for s in surveys
        ]
    )


def _likert_kb(question_id: int):
    labels = ["1\n😞", "2\n🙁", "3\n😐", "4\n🙂", "5\n😄"]
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(lbl, callback_data=f"ans_{question_id}_{i + 1}")
                for i, lbl in enumerate(labels)
            ]
        ]
    )


def _mcq_kb(question_id: int, options):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    opt["option_text"], callback_data=f"ans_{question_id}_{opt['id']}"
                )
            ]
            for opt in options
        ]
    )


def _ranking_kb(question_id: int, remaining_options):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    opt["option_text"], callback_data=f"rank_{question_id}_{opt['id']}"
                )
            ]
            for opt in remaining_options
        ]
    )


# ── Question sender ───────────────────────────────────────────────────────────


async def _send_question(query, context: ContextTypes.DEFAULT_TYPE) -> bool:
    questions = context.user_data["sq_questions"]
    idx = context.user_data["sq_index"]

    if idx >= len(questions):
        return True

    q = questions[idx]
    qtype = q["question_type"]
    q_id = q["id"]
    total = len(questions)

    header = f"*Question {idx + 1} of {total}*\n\n{q['question_text']}"

    if qtype == "likert":
        await query.edit_message_text(
            header, reply_markup=_likert_kb(q_id), parse_mode="Markdown"
        )

    elif qtype == "multiple_choice":
        options = db.get_options_by_question(q_id)
        await query.edit_message_text(
            header, reply_markup=_mcq_kb(q_id, options), parse_mode="Markdown"
        )

    elif qtype == "ranking":
        options = db.get_options_by_question(q_id)
        context.user_data["sq_rank_all"] = {
            str(o["id"]): o["option_text"] for o in options
        }
        context.user_data["sq_rank_remaining"] = [dict(o) for o in options]
        context.user_data["sq_rank_selected"] = []

        await query.edit_message_text(
            header, reply_markup=_ranking_kb(q_id, options), parse_mode="Markdown"
        )

    return False


# ── Finish survey (SQLite save) ───────────────────────────────────────────────


async def _finish_survey(query, context: ContextTypes.DEFAULT_TYPE):
    survey_id = context.user_data["sq_survey_id"]
    responses = context.user_data["sq_responses"]
    user = query.from_user

    try:
        db.save_response(survey_id=survey_id, user_id=user.id, responses=responses)

        db.mark_survey_completed(survey_id, user.id)

        await query.edit_message_text("🎉 Survey completed! Your responses are saved.")

    except Exception as e:
        print("ERROR:", e)
        await query.edit_message_text("Error saving responses.")


# ── Entry ─────────────────────────────────────────────────────────────────────


async def surveys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    surveys = db.get_active_surveys()

    if not surveys:
        await update.message.reply_text("No surveys available.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Select a survey:", reply_markup=_surveys_kb(surveys)
    )

    return SELECT_SURVEY


# ── Select survey ─────────────────────────────────────────────────────────────


async def select_survey_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    survey_id = int(query.data.split("_")[-1])
    user_id = update.effective_user.id

    if db.has_user_completed_survey(survey_id, user_id):
        await query.edit_message_text("You already completed this survey.")
        return SELECT_SURVEY

    survey = db.get_survey_by_id(survey_id)
    questions = db.get_questions_by_survey(survey_id)

    context.user_data.update(
        {
            "sq_survey_id": survey_id,
            "sq_questions": [dict(q) for q in questions],
            "sq_index": 0,
            "sq_responses": [],
        }
    )

    await query.edit_message_text(
        f"{survey['title']}\nStart?",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Start", callback_data="survey_start_yes")]]
        ),
    )

    return CONFIRM_START


# ── Confirm start ─────────────────────────────────────────────────────────────


async def confirm_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    done = await _send_question(query, context)

    if done:
        await _finish_survey(query, context)
        return ConversationHandler.END

    return ANSWERING


# ── Answering ─────────────────────────────────────────────────────────────────


async def answering_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    questions = context.user_data["sq_questions"]
    idx = context.user_data["sq_index"]
    question = questions[idx]

    qtype = question["question_type"]
    q_id = question["id"]

    # Likert
    if qtype == "likert":
        score = int(data.split("_")[-1])

        context.user_data["sq_responses"].append(
            {
                "question_id": q_id,
                "question_num": idx + 1,
                "question_text": question["question_text"],
                "answer": score,
            }
        )

    # MCQ
    elif qtype == "multiple_choice":
        opt_id = int(data.split("_")[-1])

        options = db.get_options_by_question(q_id)
        opt_map = {o["id"]: o["option_text"] for o in options}

        context.user_data["sq_responses"].append(
            {
                "question_id": q_id,
                "question_num": idx + 1,
                "question_text": question["question_text"],
                "answer": opt_map.get(opt_id),
            }
        )

    # Ranking
    elif qtype == "ranking":
        opt_id = int(data.split("_")[-1])
        selected = context.user_data.get("sq_rank_selected", [])

        selected.append(opt_id)
        context.user_data["sq_rank_selected"] = selected

        if len(selected) < len(context.user_data["sq_rank_all"]):
            return ANSWERING

        context.user_data["sq_responses"].append(
            {
                "question_id": q_id,
                "question_num": idx + 1,
                "question_text": question["question_text"],
                "answer": selected,
            }
        )

    context.user_data["sq_index"] += 1

    done = await _send_question(query, context)

    if done:
        await _finish_survey(query, context)
        return ConversationHandler.END

    return ANSWERING


# ── Handler ───────────────────────────────────────────────────────────────────


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
