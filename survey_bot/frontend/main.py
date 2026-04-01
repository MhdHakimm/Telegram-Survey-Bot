import streamlit as st
import json
import os

# ── Config ─────────────────────────────────────────────
st.set_page_config(page_title="Survey Creator", layout="wide")

SURVEY_DIR = "surveys"
os.makedirs(SURVEY_DIR, exist_ok=True)


# ── Helpers ────────────────────────────────────────────
def get_all_surveys():
    return [f for f in os.listdir(SURVEY_DIR) if f.endswith(".json")]


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


# ── State ──────────────────────────────────────────────
if "mode" not in st.session_state:
    st.session_state.mode = "list"  # list | edit

if "questions" not in st.session_state:
    st.session_state.questions = []

if "title" not in st.session_state:
    st.session_state.title = ""

if "filename" not in st.session_state:
    st.session_state.filename = None

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
            if st.button(s, key=s):
                data = load_survey(s)
                st.session_state.title = data.get("title", "")
                st.session_state.questions = data.get("questions", [])
                st.session_state.filename = s
                st.session_state.mode = "edit"

        with col2:
            if st.button("🗑️", key=f"del_{s}"):
                os.remove(os.path.join(SURVEY_DIR, s))
                st.rerun()

    st.divider()

    if st.button("➕ Create New Survey"):
        st.session_state.title = ""
        st.session_state.questions = []
        st.session_state.filename = f"survey_{len(surveys)+1}.json"
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
            autosave()
            st.success("Saved")
