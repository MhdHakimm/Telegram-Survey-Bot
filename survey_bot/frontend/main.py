import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
import os

# ── Setup ─────────────────────────────────────────────
load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

st.set_page_config(page_title="Survey Creator Pro", layout="wide")


# ── Helpers ────────────────────────────────────────────
def get_surveys():
    res = supabase.table("survey").select("id, title").execute()
    return res.data if res.data else []


def load_survey_from_db(survey_id):
    res = supabase.table("survey").select("*").eq("id", survey_id).execute()
    survey = res.data[0]

    st.session_state.title = survey["title"]

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
            "meta": q.get("meta", {}) or {},
        }

        # MCQ options
        if q["question_type"] == "mcq":
            opt_res = (
                supabase.table("option")
                .select("*")
                .eq("question_id", q["id"])
                .execute()
            )
            question["meta"]["options"] = [o["option_text"] for o in opt_res.data]

        questions.append(question)

    st.session_state.questions = questions


def save_survey_to_db(title, questions):
    survey_id = st.session_state.survey_id

    # CREATE
    if not survey_id:
        res = supabase.table("survey").insert({"title": title}).execute()
        survey_id = res.data[0]["id"]
        st.session_state.survey_id = survey_id

    else:
        supabase.table("survey").update({"title": title}).eq("id", survey_id).execute()

        # delete old
        old_q = (
            supabase.table("question").select("id").eq("survey_id", survey_id).execute()
        )

        for q in old_q.data:
            supabase.table("option").delete().eq("question_id", q["id"]).execute()

        supabase.table("question").delete().eq("survey_id", survey_id).execute()

    # insert new
    for i, q in enumerate(questions):
        q_res = (
            supabase.table("question")
            .insert(
                {
                    "survey_id": survey_id,
                    "question_text": q["text"],
                    "question_type": q["type"],
                    "order_index": i,
                    "meta": q.get("meta", {}),  # ⭐ IMPORTANT
                }
            )
            .execute()
        )

        question_id = q_res.data[0]["id"]

        if q["type"] == "mcq":
            for opt in q["meta"].get("options", []):
                supabase.table("option").insert(
                    {"question_id": question_id, "option_text": opt}
                ).execute()


# ── State ──────────────────────────────────────────────
if "mode" not in st.session_state:
    st.session_state.mode = "list"

if "questions" not in st.session_state:
    st.session_state.questions = []

if "title" not in st.session_state:
    st.session_state.title = ""

if "survey_id" not in st.session_state:
    st.session_state.survey_id = None


# ── UI ─────────────────────────────────────────────────
st.title("Survey Creator Pro")

# ======================================================
# LIST VIEW
# ======================================================
if st.session_state.mode == "list":
    st.subheader("Your Surveys")

    surveys = get_surveys()

    if not surveys:
        st.write("No surveys yet")

    for s in surveys:
        col1, col2 = st.columns([4, 1])

        with col1:
            if st.button(s["title"], key=str(s["id"])):
                st.session_state.survey_id = s["id"]
                st.session_state.mode = "edit"
                load_survey_from_db(s["id"])
                st.rerun()

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
        st.rerun()


# ======================================================
# EDIT VIEW
# ======================================================
if st.session_state.mode == "edit":
    st.subheader("Edit Survey")

    st.session_state.title = st.text_input("Survey Title", value=st.session_state.title)

    st.divider()

    # Add Question
    st.write("### Add Question")

    q_text = st.text_input("Question")
    q_type = st.selectbox("Type", ["mcq", "text", "ranking", "likert", "image"])

    q_meta = {}

    if q_type == "mcq":
        opt_input = st.text_area("Options (one per line)")
        q_meta["options"] = [o.strip() for o in opt_input.split("\n") if o.strip()]

    elif q_type == "ranking":
        q_meta["num_items"] = st.slider("Number of items", 2, 5, 3)

    elif q_type == "likert":
        q_meta["scale"] = st.slider("Scale", 3, 6, 3)

    elif q_type == "image":
        q_meta["image_url"] = st.text_input("Image URL")

    # skip logic
    skip_to = st.number_input("Skip to question (0 = none)", 0)
    if skip_to > 0:
        q_meta["skip_to"] = int(skip_to)

    if st.button("Add Question"):
        if q_text:
            st.session_state.questions.append(
                {"text": q_text, "type": q_type, "meta": q_meta}
            )
            st.rerun()

    st.divider()

    # Preview
    st.write("### Preview")

    for i, q in enumerate(st.session_state.questions):
        st.markdown(f"**{i+1}. {q['text']}**")

        if q["type"] == "mcq":
            st.radio("Select", q["meta"].get("options", []), key=f"p_{i}")

        elif q["type"] == "text":
            st.text_input("Answer", key=f"t_{i}")

        elif q["type"] == "ranking":
            for r in range(q["meta"].get("num_items", 3)):
                st.text_input(f"Rank {r+1}", key=f"r_{i}_{r}")

        elif q["type"] == "likert":
            cols = st.columns(q["meta"].get("scale", 3))
            for j in range(q["meta"].get("scale", 3)):
                cols[j].button(str(j + 1), key=f"l_{i}_{j}")

        elif q["type"] == "image":
            if q["meta"].get("image_url"):
                st.image(q["meta"]["image_url"])

        if q["meta"].get("skip_to"):
            st.caption(f"→ jumps to Q{q['meta']['skip_to']}")

    st.divider()

    if st.button("💾 Save"):
        save_survey_to_db(st.session_state.title, st.session_state.questions)
        st.success("Saved")

    if st.button("⬅ Back"):
        st.session_state.mode = "list"
        st.rerun()
