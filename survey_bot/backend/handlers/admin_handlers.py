"""
Admin conversation handler — fixed version.
Entry point: /admin  (only accessible to ADMIN_IDS)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

import database as db
from config import ADMIN_IDS

# ── States ────────────────────────────────────────────────────────────────────
(
    ADMIN_MAIN,
    CREATE_TITLE,
    CREATE_DESC,
    Q_MENU,
    Q_TYPE,
    Q_TEXT,
    Q_OPTION,
    EDIT_SELECT,
    EDIT_MENU,
    EDIT_TITLE_STATE,
    EDIT_DESC_STATE,
    DELETE_CONFIRM,
    EDIT_Q_SELECT,
    EDIT_Q_MENU,
    EDIT_Q_TEXT_STATE,
    EDIT_Q_OPT_MENU,
    EDIT_Q_OPT_ADD,
) = range(17)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ── Safe edit helper — swallows "message not modified" errors ─────────────────
async def safe_edit(query, text, reply_markup=None, parse_mode="Markdown"):
    try:
        await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode=parse_mode
        )
    except BadRequest as e:
        if "not modified" in str(e).lower():
            pass  # ignore — same content, not a real error
        else:
            raise


# ── Keyboards ─────────────────────────────────────────────────────────────────

def kb_admin_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 List Surveys",  callback_data="admin_list")],
        [InlineKeyboardButton("➕ Create Survey", callback_data="admin_create")],
    ])


def kb_q_type():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Likert Scale (1–5)", callback_data="qtype_likert")],
        [InlineKeyboardButton("☑️ Multiple Choice",    callback_data="qtype_mcq")],
        [InlineKeyboardButton("🔢 Ranking",            callback_data="qtype_ranking")],
    ])


def kb_q_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Question",  callback_data="q_add")],
        [InlineKeyboardButton("✅ Save & Finish", callback_data="q_done")],
    ])


def kb_survey_list(surveys):
    buttons = []
    for s in surveys:
        icon = "🟢" if s["is_active"] else "🔴"
        buttons.append([InlineKeyboardButton(
            f"{icon} {s['title']}", callback_data=f"sv_{s['id']}"
        )])
    buttons.append([InlineKeyboardButton("➕ Create Survey", callback_data="admin_create")])
    return InlineKeyboardMarkup(buttons)


def kb_survey_edit(survey_id: int, is_active: int):
    toggle = "🔴 Deactivate" if is_active else "🟢 Activate"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Edit Title",       callback_data=f"et_{survey_id}")],
        [InlineKeyboardButton("📝 Edit Description", callback_data=f"ed_{survey_id}")],
        [InlineKeyboardButton("❓ Manage Questions", callback_data=f"mq_{survey_id}")],
        [InlineKeyboardButton(toggle,                callback_data=f"tg_{survey_id}")],
        [InlineKeyboardButton("🗑️ Delete Survey",   callback_data=f"ds_{survey_id}")],
        [InlineKeyboardButton("⬅️ Back",            callback_data="admin_list")],
    ])


def kb_questions_list(questions, survey_id: int):
    type_icon = {"likert": "📊", "multiple_choice": "☑️", "ranking": "🔢"}
    buttons = []
    for q in questions:
        icon = type_icon.get(q["question_type"], "❓")
        preview = q["question_text"][:38] + ("…" if len(q["question_text"]) > 38 else "")
        buttons.append([InlineKeyboardButton(
            f"{icon} {preview}", callback_data=f"eq_{q['id']}"
        )])
    buttons.append([InlineKeyboardButton("➕ Add Question", callback_data=f"aq_{survey_id}")])
    buttons.append([InlineKeyboardButton("⬅️ Back",         callback_data=f"sv_{survey_id}")])
    return InlineKeyboardMarkup(buttons)


def kb_question_edit(question_id: int, question_type: str, survey_id: int):
    buttons = [
        [InlineKeyboardButton("✏️ Edit Question Text", callback_data=f"eqt_{question_id}_{survey_id}")],
    ]
    if question_type in ("multiple_choice", "ranking"):
        buttons.append([InlineKeyboardButton("📝 Manage Options", callback_data=f"mo_{question_id}_{survey_id}")])
    buttons.append([InlineKeyboardButton("🗑️ Delete Question", callback_data=f"dq_{question_id}_{survey_id}")])
    buttons.append([InlineKeyboardButton("⬅️ Back",            callback_data=f"mq_{survey_id}")])
    return InlineKeyboardMarkup(buttons)


def kb_options_manage(options, question_id: int, survey_id: int):
    buttons = []
    for opt in options:
        buttons.append([InlineKeyboardButton(
            f"🗑️ {opt['option_text']}", callback_data=f"do_{opt['id']}_{question_id}_{survey_id}"
        )])
    buttons.append([InlineKeyboardButton("➕ Add Option", callback_data=f"ao_{question_id}_{survey_id}")])
    buttons.append([InlineKeyboardButton("⬅️ Back",       callback_data=f"eq_{question_id}")])
    return InlineKeyboardMarkup(buttons)


# ── Shared screen renderers ───────────────────────────────────────────────────

async def show_main_menu(query):
    await safe_edit(query, "👋 *Admin Panel*\n\nWhat would you like to do?", kb_admin_main())


async def show_survey_list(query):
    surveys = db.get_all_surveys()
    if not surveys:
        await safe_edit(
            query,
            "📋 No surveys yet. Create the first one!",
            InlineKeyboardMarkup([[InlineKeyboardButton("➕ Create Survey", callback_data="admin_create")]]),
        )
    else:
        await safe_edit(query, "📋 *All Surveys*\nSelect one to manage:", kb_survey_list(surveys))


async def show_survey_detail(query, survey_id: int):
    survey = db.get_survey_by_id(survey_id)
    questions = db.get_questions_by_survey(survey_id)
    status = "🟢 Active" if survey["is_active"] else "🔴 Inactive"
    desc = survey["description"] or "_No description_"
    text = (
        f"📋 *{survey['title']}*\n"
        f"📄 {desc}\n"
        f"Status: {status}\n"
        f"Questions: {len(questions)}"
    )
    await safe_edit(query, text, kb_survey_edit(survey_id, survey["is_active"]))


async def show_questions_list(query, survey_id: int):
    questions = db.get_questions_by_survey(survey_id)
    if not questions:
        await safe_edit(
            query,
            "❓ No questions yet.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add Question", callback_data=f"aq_{survey_id}")],
                [InlineKeyboardButton("⬅️ Back",         callback_data=f"sv_{survey_id}")],
            ]),
        )
    else:
        await safe_edit(query, "❓ *Questions*\nSelect one to edit:", kb_questions_list(questions, survey_id))


async def show_question_detail(query, question_id: int, survey_id: int):
    question = db.get_question_by_id(question_id)
    icon = {"likert": "📊", "multiple_choice": "☑️", "ranking": "🔢"}.get(question["question_type"], "❓")
    await safe_edit(
        query,
        f"{icon} *{question['question_text']}*\nType: {question['question_type'].replace('_', ' ').title()}",
        kb_question_edit(question_id, question["question_type"], survey_id),
    )


async def show_options_list(query, question_id: int, survey_id: int):
    question = db.get_question_by_id(question_id)
    options = db.get_options_by_question(question_id)
    await safe_edit(
        query,
        f"📝 Options for: *{question['question_text']}*\n\nTap 🗑️ to remove an option.",
        kb_options_manage(options, question_id, survey_id),
    )


# ── /admin entry ──────────────────────────────────────────────────────────────

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ You are not authorised.")
        return ConversationHandler.END
    context.user_data.clear()
    await update.message.reply_text(
        "👋 *Admin Panel*\n\nWhat would you like to do?",
        reply_markup=kb_admin_main(),
        parse_mode="Markdown",
    )
    return ADMIN_MAIN


# ── Universal router ──────────────────────────────────────────────────────────
# This single callback handler routes ALL button presses from any state.

async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── Navigation ────────────────────────────────────────────────────────────

    if data == "admin_list":
        await show_survey_list(query)
        return EDIT_SELECT

    if data == "admin_create":
        await safe_edit(query, "📝 *Create a New Survey*\n\nEnter the *survey title*:")
        return CREATE_TITLE

    if data.startswith("sv_"):                          # survey detail
        survey_id = int(data[3:])
        context.user_data["survey_id"] = survey_id
        await show_survey_detail(query, survey_id)
        return EDIT_MENU

    if data.startswith("mq_"):                          # manage questions
        survey_id = int(data[3:])
        context.user_data["survey_id"] = survey_id
        await show_questions_list(query, survey_id)
        return EDIT_Q_SELECT

    if data.startswith("eq_"):                          # question detail
        question_id = int(data[3:])
        question = db.get_question_by_id(question_id)
        survey_id = question["survey_id"]
        context.user_data["question_id"] = question_id
        context.user_data["survey_id"] = survey_id
        await show_question_detail(query, question_id, survey_id)
        return EDIT_Q_MENU

    if data.startswith("mo_"):                          # manage options
        parts = data[3:].split("_")
        question_id, survey_id = int(parts[0]), int(parts[1])
        context.user_data["question_id"] = question_id
        context.user_data["survey_id"] = survey_id
        await show_options_list(query, question_id, survey_id)
        return EDIT_Q_OPT_MENU

    # ── Add question (from questions list) ────────────────────────────────────

    if data.startswith("aq_"):
        survey_id = int(data[3:])
        context.user_data["survey_id"] = survey_id
        context.user_data["new_q_options"] = []
        await safe_edit(query, "Select the *question type*:", kb_q_type())
        return Q_TYPE

    if data == "q_add":
        context.user_data["new_q_options"] = []
        await safe_edit(query, "Select the *question type*:", kb_q_type())
        return Q_TYPE

    if data == "q_done":
        survey_id = context.user_data.get("survey_id")
        survey = db.get_survey_by_id(survey_id)
        questions = db.get_questions_by_survey(survey_id)
        await safe_edit(
            query,
            f"✅ Survey *{survey['title']}* saved with *{len(questions)}* question(s)!\n\nUse /admin to manage surveys.",
        )
        return ConversationHandler.END

    # ── Question type selection ───────────────────────────────────────────────

    if data.startswith("qtype_"):
        type_map = {"qtype_likert": "likert", "qtype_mcq": "multiple_choice", "qtype_ranking": "ranking"}
        context.user_data["new_q_type"] = type_map[data]
        context.user_data["new_q_options"] = []
        await safe_edit(query, f"📝 Enter the *question text*:", parse_mode="Markdown")
        return Q_TEXT

    # ── Option management ─────────────────────────────────────────────────────

    if data == "opt_more":
        await safe_edit(query, "Enter the next option:")
        return Q_OPTION

    if data == "opt_done":
        options = context.user_data.get("new_q_options", [])
        if len(options) < 2:
            await safe_edit(query, "⚠️ Please add at least *2 options*. Enter another option:")
            return Q_OPTION
        survey_id = context.user_data["survey_id"]
        q_text = context.user_data["new_q_text"]
        qtype = context.user_data["new_q_type"]
        question_id = db.add_question(survey_id, q_text, qtype)
        for opt in options:
            db.add_option(question_id, opt)
        context.user_data["new_q_options"] = []
        await safe_edit(
            query,
            f"✅ Question added with *{len(options)}* options!\n\nAdd another question or finish?",
            kb_q_menu(),
        )
        return Q_MENU

    # ── Survey actions ────────────────────────────────────────────────────────

    if data.startswith("et_"):                          # edit title
        context.user_data["survey_id"] = int(data[3:])
        await safe_edit(query, "✏️ Enter the *new title*:")
        return EDIT_TITLE_STATE

    if data.startswith("ed_"):                          # edit description
        context.user_data["survey_id"] = int(data[3:])
        await safe_edit(query, "📝 Enter the *new description* (or type `skip` to clear):")
        return EDIT_DESC_STATE

    if data.startswith("tg_"):                          # toggle active
        survey_id = int(data[3:])
        db.toggle_survey_active(survey_id)
        await show_survey_detail(query, survey_id)
        return EDIT_MENU

    if data.startswith("ds_"):                          # delete survey
        survey_id = int(data[3:])
        context.user_data["survey_id"] = survey_id
        survey = db.get_survey_by_id(survey_id)
        await safe_edit(
            query,
            f"⚠️ Are you sure you want to *permanently delete* `{survey['title']}`?",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑️ Yes, Delete", callback_data=f"cd_{survey_id}")],
                [InlineKeyboardButton("❌ Cancel",       callback_data=f"sv_{survey_id}")],
            ]),
        )
        return DELETE_CONFIRM

    if data.startswith("cd_"):                          # confirm delete
        survey_id = int(data[3:])
        db.delete_survey(survey_id)
        await show_survey_list(query)
        return EDIT_SELECT

    # ── Question actions ──────────────────────────────────────────────────────

    if data.startswith("eqt_"):                         # edit question text
        parts = data[4:].split("_")
        question_id, survey_id = int(parts[0]), int(parts[1])
        context.user_data["question_id"] = question_id
        context.user_data["survey_id"] = survey_id
        await safe_edit(query, "✏️ Enter the *new question text*:")
        return EDIT_Q_TEXT_STATE

    if data.startswith("dq_"):                          # delete question
        parts = data[3:].split("_")
        question_id, survey_id = int(parts[0]), int(parts[1])
        db.delete_question(question_id)
        await show_questions_list(query, survey_id)
        return EDIT_Q_SELECT

    # ── Option actions ────────────────────────────────────────────────────────

    if data.startswith("do_"):                          # delete option
        parts = data[3:].split("_")
        opt_id, question_id, survey_id = int(parts[0]), int(parts[1]), int(parts[2])
        db.delete_option(opt_id)
        await show_options_list(query, question_id, survey_id)
        return EDIT_Q_OPT_MENU

    if data.startswith("ao_"):                          # add option
        parts = data[3:].split("_")
        question_id, survey_id = int(parts[0]), int(parts[1])
        context.user_data["question_id"] = question_id
        context.user_data["survey_id"] = survey_id
        await safe_edit(query, "➕ Enter the *new option text*:")
        return EDIT_Q_OPT_ADD

    # Fallback — go back to main menu
    await show_main_menu(query)
    return ADMIN_MAIN


# ── Text input handlers ───────────────────────────────────────────────────────

async def create_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_survey_title"] = update.message.text.strip()
    await update.message.reply_text(
        "📄 Enter the *survey description* (or type `skip` to leave blank):",
        parse_mode="Markdown",
    )
    return CREATE_DESC


async def create_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    desc = "" if raw.lower() == "skip" else raw
    survey_id = db.create_survey(context.user_data["new_survey_title"], desc)
    context.user_data["survey_id"] = survey_id
    context.user_data["new_q_options"] = []
    await update.message.reply_text(
        f"✅ Survey *{context.user_data['new_survey_title']}* created!\n\nNow add questions:",
        reply_markup=kb_q_menu(),
        parse_mode="Markdown",
    )
    return Q_MENU


async def q_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["new_q_text"] = text
    qtype = context.user_data["new_q_type"]

    if qtype == "likert":
        survey_id = context.user_data["survey_id"]
        db.add_question(survey_id, text, "likert")
        await update.message.reply_text(
            "✅ Likert question added!\n_(Scale: 1 = Strongly Disagree … 5 = Strongly Agree)_\n\n"
            "Add another question or finish?",
            reply_markup=kb_q_menu(),
            parse_mode="Markdown",
        )
        return Q_MENU

    await update.message.reply_text("Enter the *first option*:", parse_mode="Markdown")
    return Q_OPTION


async def q_option_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    option_text = update.message.text.strip()
    options = context.user_data.setdefault("new_q_options", [])
    options.append(option_text)
    await update.message.reply_text(
        f"Option {len(options)} added: *{option_text}*\n\nAdd more or finish?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Another Option",  callback_data="opt_more")],
            [InlineKeyboardButton("✅ Done Adding Options", callback_data="opt_done")],
        ]),
        parse_mode="Markdown",
    )
    return Q_OPTION


async def edit_title_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    survey_id = context.user_data["survey_id"]
    db.update_survey_title(survey_id, update.message.text.strip())
    survey = db.get_survey_by_id(survey_id)
    await update.message.reply_text(
        f"✅ Title updated to *{survey['title']}*!",
        reply_markup=kb_survey_edit(survey_id, survey["is_active"]),
        parse_mode="Markdown",
    )
    return EDIT_MENU


async def edit_desc_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    survey_id = context.user_data["survey_id"]
    raw = update.message.text.strip()
    db.update_survey_description(survey_id, "" if raw.lower() == "skip" else raw)
    survey = db.get_survey_by_id(survey_id)
    await update.message.reply_text(
        "✅ Description updated!",
        reply_markup=kb_survey_edit(survey_id, survey["is_active"]),
        parse_mode="Markdown",
    )
    return EDIT_MENU


async def edit_q_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question_id = context.user_data["question_id"]
    survey_id = context.user_data["survey_id"]
    db.update_question_text(question_id, update.message.text.strip())
    question = db.get_question_by_id(question_id)
    await update.message.reply_text(
        f"✅ Question updated!\n\n*{question['question_text']}*",
        reply_markup=kb_question_edit(question_id, question["question_type"], survey_id),
        parse_mode="Markdown",
    )
    return EDIT_Q_MENU


async def edit_q_opt_add_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question_id = context.user_data["question_id"]
    survey_id = context.user_data["survey_id"]
    db.add_option(question_id, update.message.text.strip())
    question = db.get_question_by_id(question_id)
    options = db.get_options_by_question(question_id)
    await update.message.reply_text(
        f"✅ Option added!\n\nOptions for: *{question['question_text']}*",
        reply_markup=kb_options_manage(options, question_id, survey_id),
        parse_mode="Markdown",
    )
    return EDIT_Q_OPT_MENU


# ── Cancel ────────────────────────────────────────────────────────────────────

async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Admin session ended. Type /admin to start again.")
    return ConversationHandler.END


# ── Build handler ─────────────────────────────────────────────────────────────

def get_admin_handler() -> ConversationHandler:
    # One universal router handles ALL callback queries in ALL states
    universal_cb = CallbackQueryHandler(router)

    return ConversationHandler(
        entry_points=[CommandHandler("admin", admin_command)],
        states={
            ADMIN_MAIN:        [universal_cb],
            CREATE_TITLE:      [MessageHandler(filters.TEXT & ~filters.COMMAND, create_title), universal_cb],
            CREATE_DESC:       [MessageHandler(filters.TEXT & ~filters.COMMAND, create_desc), universal_cb],
            Q_MENU:            [universal_cb],
            Q_TYPE:            [universal_cb],
            Q_TEXT:            [MessageHandler(filters.TEXT & ~filters.COMMAND, q_text), universal_cb],
            Q_OPTION:          [MessageHandler(filters.TEXT & ~filters.COMMAND, q_option_text), universal_cb],
            EDIT_SELECT:       [universal_cb],
            EDIT_MENU:         [universal_cb],
            EDIT_TITLE_STATE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_title_input), universal_cb],
            EDIT_DESC_STATE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_desc_input), universal_cb],
            DELETE_CONFIRM:    [universal_cb],
            EDIT_Q_SELECT:     [universal_cb],
            EDIT_Q_MENU:       [universal_cb],
            EDIT_Q_TEXT_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_q_text_input), universal_cb],
            EDIT_Q_OPT_MENU:   [universal_cb],
            EDIT_Q_OPT_ADD:    [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_q_opt_add_input), universal_cb],
        },
        fallbacks=[CommandHandler("cancel", cancel_admin)],
        allow_reentry=True,
        name="admin_conversation",
        per_message=False,
    )