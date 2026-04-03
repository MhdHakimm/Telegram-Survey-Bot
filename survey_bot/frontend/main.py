# import streamlit as st
# import json
# import os

# # ── Config ─────────────────────────────────────────────
# st.set_page_config(page_title="Survey Creator", layout="wide")

# SURVEY_DIR = "surveys"
# os.makedirs(SURVEY_DIR, exist_ok=True)


# # ── Helpers ────────────────────────────────────────────
# def get_all_surveys():
#     return [f for f in os.listdir(SURVEY_DIR) if f.endswith(".json")]


# def load_survey(filename):
#     with open(os.path.join(SURVEY_DIR, filename), "r") as f:
#         return json.load(f)


# def save_survey(filename, data):
#     with open(os.path.join(SURVEY_DIR, filename), "w") as f:
#         json.dump(data, f, indent=4)


# def autosave():
#     if not st.session_state.filename:
#         return

#     data = {"title": st.session_state.title, "questions": st.session_state.questions}

#     save_survey(st.session_state.filename, data)


# # ── State ──────────────────────────────────────────────
# if "mode" not in st.session_state:
#     st.session_state.mode = "list"  # list | edit

# if "questions" not in st.session_state:
#     st.session_state.questions = []

# if "title" not in st.session_state:
#     st.session_state.title = ""

# if "filename" not in st.session_state:
#     st.session_state.filename = None

# # ── UI ─────────────────────────────────────────────────
# st.title("Survey Creator")

# # ======================================================
# # 📋 LIST VIEW
# # ======================================================
# if st.session_state.mode == "list":

#     st.subheader("Your Surveys")

#     surveys = get_all_surveys()

#     if not surveys:
#         st.write("No surveys yet")

#     for s in surveys:
#         col1, col2 = st.columns([4, 1])

#         with col1:
#             if st.button(s, key=s):
#                 data = load_survey(s)
#                 st.session_state.title = data.get("title", "")
#                 st.session_state.questions = data.get("questions", [])
#                 st.session_state.filename = s
#                 st.session_state.mode = "edit"

#         with col2:
#             if st.button("🗑️", key=f"del_{s}"):
#                 os.remove(os.path.join(SURVEY_DIR, s))
#                 st.rerun()

#     st.divider()

#     if st.button("➕ Create New Survey"):
#         st.session_state.title = ""
#         st.session_state.questions = []
#         st.session_state.filename = f"survey_{len(surveys)+1}.json"
#         st.session_state.mode = "edit"

# # ======================================================
# # ✏️ EDIT VIEW
# # ======================================================
# if st.session_state.mode == "edit":

#     st.subheader("Edit Survey")

#     # Title
#     st.session_state.title = st.text_input("Survey Title", value=st.session_state.title)

#     st.divider()

#     # ── Add Question ───────────────────────────────────
#     st.write("Add Question")

#     q_text = st.text_input("Question")
#     q_type = st.selectbox("Type", ["mcq", "text"])

#     options = []
#     if q_type == "mcq":
#         opt1 = st.text_input("Option 1")
#         opt2 = st.text_input("Option 2")
#         opt3 = st.text_input("Option 3")

#         options = [o for o in [opt1, opt2, opt3] if o]

#     if st.button("Add Question"):
#         if q_text:
#             st.session_state.questions.append(
#                 {"text": q_text, "type": q_type, "options": options}
#             )
#             autosave()

#     st.divider()

#     # ── Existing Questions (EDIT + DELETE) ─────────────
#     st.write("Questions")

#     for i, q in enumerate(st.session_state.questions):
#         col1, col2 = st.columns([5, 1])

#         with col1:
#             new_text = st.text_input(f"Q{i+1}", value=q["text"], key=f"text_{i}")
#             st.session_state.questions[i]["text"] = new_text

#         with col2:
#             if st.button("❌", key=f"del_q_{i}"):
#                 st.session_state.questions.pop(i)
#                 autosave()
#                 st.rerun()

#         if q["type"] == "mcq":
#             for j, opt in enumerate(q["options"]):
#                 new_opt = st.text_input(f"Option {j+1}", value=opt, key=f"opt_{i}_{j}")
#                 st.session_state.questions[i]["options"][j] = new_opt

#     st.divider()

#     # ── Preview ────────────────────────────────────────
#     st.write("Preview")

#     for i, q in enumerate(st.session_state.questions):
#         st.write(f"{i+1}. {q['text']}")

#         if q["type"] == "mcq":
#             for opt in q["options"]:
#                 st.button(opt, key=f"prev_{i}_{opt}")
#         else:
#             st.text_input("Answer", key=f"prev_input_{i}")

#     st.divider()

#     # ── Navigation ─────────────────────────────────────
#     col1, col2 = st.columns(2)

#     with col1:
#         if st.button("⬅ Back"):
#             st.session_state.mode = "list"
#             st.rerun()

#     with col2:
#         if st.button("💾 Save"):
#             autosave()
#             st.success("Saved")
#########################################################################################################
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
st.set_page_config(page_title="Survey Creator Pro", layout="wide")

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
    st.session_state.mode = "list"

if "questions" not in st.session_state:
    st.session_state.questions = []

if "title" not in st.session_state:
    st.session_state.title = ""

if "filename" not in st.session_state:
    st.session_state.filename = None

if "survey_id" not in st.session_state:
    st.session_state.survey_id = None

# ── UI ─────────────────────────────────────────────────
st.title("Survey Creator Pro")

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
        st.rerun()

# ======================================================
# ✏️ EDIT VIEW
# ======================================================
if st.session_state.mode == "edit":
    st.subheader(f"Editing: {st.session_state.filename}")
    st.session_state.title = st.text_input("Survey Title", value=st.session_state.title)

    st.divider()

    # ── Add Question ───────────────────────────────────
    st.write("### Add New Question")
    q_text = st.text_input("Question Text")
    q_type = st.selectbox("Type", ["mcq", "text", "ranking", "likert", "image"])

    # Metadata for new features
    q_metadata = {}

    if q_type == "ranking":
        q_metadata["num_items"] = st.slider("Number of ranking options", 2, 5, 3)

    elif q_type == "likert":
        q_metadata["scale"] = st.slider("Likert Scale (Points)", 3, 6, 3)

    elif q_type == "image":
        q_metadata["image_url"] = st.text_input("Image URL (Direct link)")

    elif q_type == "mcq":
        opt_input = st.text_area("Options (One per line)")
        q_metadata["options"] = [o.strip() for o in opt_input.split("\n") if o.strip()]

    # Skip Logic Configuration
    st.write("**Skip Logic** (Optional)")
    target_q = st.number_input(
        "If answered, skip to Question # (0 for none)", min_value=0, value=0
    )
    if target_q > 0:
        q_metadata["skip_to"] = int(target_q)

    if st.button("Add Question"):
        if q_text:
            new_q = {"text": q_text, "type": q_type, "meta": q_metadata}
            st.session_state.questions.append(new_q)
            autosave()
            st.rerun()

    st.divider()

    # ── Existing Questions (Management) ─────────────
    st.write("### Survey Structure")

    for i, q in enumerate(st.session_state.questions):
        with st.expander(f"Q{i+1}: {q['text']} ({q['type'].upper()})"):
            col1, col2 = st.columns([4, 1])

            with col1:
                q["text"] = st.text_input(
                    f"Edit Text Q{i+1}", value=q["text"], key=f"edit_text_{i}"
                )

                # Dynamic fields based on type
                if q["type"] == "ranking":
                    q["meta"]["num_items"] = st.slider(
                        f"Options for Q{i+1}",
                        2,
                        5,
                        q["meta"].get("num_items", 3),
                        key=f"rank_{i}",
                    )

                if q["type"] == "likert":
                    q["meta"]["scale"] = st.slider(
                        f"Scale for Q{i+1}",
                        3,
                        6,
                        q["meta"].get("scale", 3),
                        key=f"likert_{i}",
                    )

                if q["type"] == "image":
                    q["meta"]["image_url"] = st.text_input(
                        f"Image URL Q{i+1}",
                        value=q["meta"].get("image_url", ""),
                        key=f"img_{i}",
                    )

                # Inline Skip Logic Edit
                q["meta"]["skip_to"] = st.number_input(
                    f"Skip to Q# (Current: Q{i+1})",
                    value=q["meta"].get("skip_to", 0),
                    key=f"skip_{i}",
                )

            with col2:
                if st.button("❌ Remove", key=f"del_q_{i}"):
                    st.session_state.questions.pop(i)
                    autosave()
                    st.rerun()

    st.divider()

    # ── Preview ────────────────────────────────────────
    st.write("### Live Preview")

    for i, q in enumerate(st.session_state.questions):
        st.markdown(f"**{i+1}. {q['text']}**")

        if q["type"] == "image" and q["meta"].get("image_url"):
            st.image(q["meta"]["image_url"], width=300)

        if q["type"] == "mcq":
            st.radio(
                "Select one", q["meta"].get("options", ["No options"]), key=f"p_mcq_{i}"
            )

        elif q["type"] == "ranking":
            st.write("Rank these (1 = Highest):")
            for r in range(q["meta"].get("num_items", 3)):
                st.text_input(f"Rank {r+1}", key=f"p_rank_{i}_{r}")

        elif q["type"] == "likert":
            cols = st.columns(q["meta"].get("scale", 3))
            for score in range(q["meta"].get("scale", 3)):
                cols[score].button(
                    str(score + 1),
                    key=f"p_likert_{i}_{score}",
                    use_container_width=True,
                )

        elif q["type"] == "text":
            st.text_input("Your answer", key=f"p_text_{i}")

        if q["meta"].get("skip_to", 0) > 0:
            st.caption(
                f"↳ *Logic: After this, jump to Question {q['meta']['skip_to']}*"
            )
        st.write("")

    # ── Navigation ─────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅ Back to Menu"):
            st.session_state.mode = "list"
            st.rerun()
    with col2:
        if st.button("💾 Save"):
            save_survey_to_db(st.session_state.title, st.session_state.questions)
            st.success("Saved to Supabase")
