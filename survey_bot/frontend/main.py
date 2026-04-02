import streamlit as st
import json
import os

# supabase client
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


# ── Config ─────────────────────────────────────────────
st.set_page_config(page_title="Survey Creator", layout="wide")

SURVEY_DIR = "surveys"
os.makedirs(SURVEY_DIR, exist_ok=True)


# ── Helpers ────────────────────────────────────────────
def get_all_surveys():
    res = (
        supabase.table("survey")
        .select("id, title")
        .order("created_at", desc=True)
        .execute()
    )

    return res.data if res.data else []


def load_survey(filename):
    with open(os.path.join(SURVEY_DIR, filename), "r") as f:
        return json.load(f)


def save_survey(filename, data):
    with open(os.path.join(SURVEY_DIR, filename), "w") as f:
        json.dump(data, f, indent=4)


def autosave():
    if not st.session_state.filename:
        return

    data = {"title": st.session_state.title, "questions": st.session_state.questions}

    save_survey(st.session_state.filename, data)


def load_survey_from_db(survey_id):
    # get survey
    res = supabase.table("survey").select("*").eq("id", survey_id).execute()
    survey = res.data[0]

    st.session_state.title = survey["title"]

    # get questions
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

            question["options"] = [o["option_text"] for o in opt_res.data]

        questions.append(question)

    st.session_state.questions = questions


def save_survey_to_db(title, questions):
    survey_id = st.session_state.survey_id

    # 🔁 CHECK if survey actually exists
    if survey_id:
        check = supabase.table("survey").select("id").eq("id", survey_id).execute()

        if not check.data:
            # survey_id invalid → reset
            survey_id = None
            st.session_state.survey_id = None

    # ➕ CREATE if needed
    if not survey_id:
        res = supabase.table("survey").insert({"title": title}).execute()

        if not res.data:
            st.error("Failed to create survey")
            return

        survey_id = res.data[0]["id"]
        st.session_state.survey_id = survey_id

    # 🔁 UPDATE existing
    else:
        supabase.table("survey").update({"title": title}).eq("id", survey_id).execute()

        # delete options first
        questions_old = (
            supabase.table("question").select("id").eq("survey_id", survey_id).execute()
        )

        for q in questions_old.data:
            supabase.table("option").delete().eq("question_id", q["id"]).execute()

        # delete questions
        supabase.table("question").delete().eq("survey_id", survey_id).execute()

    # ➕ INSERT fresh questions
    for i, q in enumerate(questions):
        q_res = (
            supabase.table("question")
            .insert(
                {
                    "survey_id": survey_id,
                    "question_text": q["text"],
                    "question_type": q["type"],
                    "order_index": i,
                }
            )
            .execute()
        )

        if not q_res.data:
            st.error("Failed to insert question")
            continue

        question_id = q_res.data[0]["id"]

        if q["type"] == "mcq":
            for opt in q["options"]:
                supabase.table("option").insert(
                    {"question_id": question_id, "option_text": opt}
                ).execute()


# ── State ──────────────────────────────────────────────
if "mode" not in st.session_state:
    st.session_state.mode = "list"  # list | edit

if "questions" not in st.session_state:
    st.session_state.questions = []

if "title" not in st.session_state:
    st.session_state.title = ""

if "filename" not in st.session_state:
    st.session_state.filename = None

if "survey_id" not in st.session_state:
    st.session_state.survey_id = None

# ── UI ─────────────────────────────────────────────────
st.title("Survey Creator")

# ======================================================
# 📋 LIST VIEW
# ======================================================
if st.session_state.mode == "list":

    st.subheader("Your Surveys")

    surveys = get_all_surveys()

    if not surveys:
        st.write("No surveys yet")

    for s in surveys:
        col1, col2 = st.columns([4, 1])

        with col1:
            if st.button(s["title"], key=str(s["id"])):
                st.session_state.survey_id = s["id"]
                st.session_state.mode = "edit"
                load_survey_from_db(s["id"])

        with col2:
            if st.button("🗑️", key=f"del_{s['id']}"):
                supabase.table("survey").delete().eq("id", s["id"]).execute()
                st.rerun()

    st.divider()

    if st.button("➕ Create New Survey"):
        st.session_state.title = ""
        st.session_state.questions = []
        st.session_state.survey_id = None
        st.session_state.mode = "edit"

# ======================================================
# ✏️ EDIT VIEW
# ======================================================
if st.session_state.mode == "edit":

    st.subheader("Edit Survey")

    # Title
    st.session_state.title = st.text_input("Survey Title", value=st.session_state.title)

    st.divider()

    # ── Add Question ───────────────────────────────────
    st.write("Add Question")

    q_text = st.text_input("Question")
    q_type = st.selectbox("Type", ["mcq", "text"])

    options = []
    if q_type == "mcq":
        opt1 = st.text_input("Option 1")
        opt2 = st.text_input("Option 2")
        opt3 = st.text_input("Option 3")

        options = [o for o in [opt1, opt2, opt3] if o]

    if st.button("Add Question"):
        if q_text:
            st.session_state.questions.append(
                {"text": q_text, "type": q_type, "options": options}
            )
            autosave()

    st.divider()

    # ── Existing Questions (EDIT + DELETE) ─────────────
    st.write("Questions")

    for i, q in enumerate(st.session_state.questions):
        col1, col2 = st.columns([5, 1])

        with col1:
            new_text = st.text_input(f"Q{i+1}", value=q["text"], key=f"text_{i}")
            st.session_state.questions[i]["text"] = new_text

        with col2:
            if st.button("❌", key=f"del_q_{i}"):
                st.session_state.questions.pop(i)
                autosave()
                st.rerun()

        if q["type"] == "mcq":
            for j, opt in enumerate(q["options"]):
                new_opt = st.text_input(f"Option {j+1}", value=opt, key=f"opt_{i}_{j}")
                st.session_state.questions[i]["options"][j] = new_opt

    st.divider()

    # ── Preview ────────────────────────────────────────
    st.write("Preview")

    for i, q in enumerate(st.session_state.questions):
        st.write(f"{i+1}. {q['text']}")

        if q["type"] == "mcq":
            for opt in q["options"]:
                st.button(opt, key=f"prev_{i}_{opt}")
        else:
            st.text_input("Answer", key=f"prev_input_{i}")

    st.divider()

    # ── Navigation ─────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        if st.button("⬅ Back"):
            st.session_state.mode = "list"
            st.rerun()

    with col2:
        if st.button("💾 Save"):
            save_survey_to_db(st.session_state.title, st.session_state.questions)
            st.success("Saved to Supabase")
