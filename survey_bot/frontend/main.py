
# MARK: New code
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
    if not res.data: return
    
    survey = res.data[0]
    st.session_state.title = survey["title"]
    st.session_state.introduction = survey.get("introduction", "") # Load Intro

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
        questions.append(question)

    st.session_state.questions = questions

def save_survey_to_db(title, intro, questions):
    survey_id = st.session_state.survey_id

    # Update/Insert Survey Table (Including Introduction)
    if not survey_id:
        res = supabase.table("survey").insert({"title": title, "introduction": intro}).execute()
        survey_id = res.data[0]["id"]
        st.session_state.survey_id = survey_id
    else:
        supabase.table("survey").update({"title": title, "introduction": intro}).eq("id", survey_id).execute()
        # Clear old questions for refresh
        supabase.table("question").delete().eq("survey_id", survey_id).execute()

    # Insert Questions
    for i, q in enumerate(questions):
        supabase.table("question").insert({
            "survey_id": survey_id,
            "question_text": q["text"],
            "question_type": q["type"],
            "order_index": i,
            "meta": q.get("meta", {}),
        }).execute()

# ── State ──────────────────────────────────────────────
if "mode" not in st.session_state: st.session_state.mode = "list"
if "questions" not in st.session_state: st.session_state.questions = []
if "title" not in st.session_state: st.session_state.title = ""
if "introduction" not in st.session_state: st.session_state.introduction = ""
if "survey_id" not in st.session_state: st.session_state.survey_id = None

# ── UI ─────────────────────────────────────────────────
st.title("Survey Creator Pro")

if st.session_state.mode == "list":
    st.subheader("Your Surveys")
    surveys = get_surveys()
    for s in surveys:
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button(s["title"], key=str(s["id"])):
                st.session_state.survey_id = s["id"]
                load_survey_from_db(s["id"])
                st.session_state.mode = "edit"
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{s['id']}"):
                supabase.table("survey").delete().eq("id", s["id"]).execute()
                st.rerun()
    
    st.divider()
    if st.button("➕ Create New Survey"):
        st.session_state.title = ""
        st.session_state.introduction = ""
        st.session_state.questions = []
        st.session_state.survey_id = None
        st.session_state.mode = "edit"
        st.rerun()

elif st.session_state.mode == "edit":
    st.subheader("Edit Survey")
    
    # ── Survey Info Section ──
    col_t, col_i = st.columns([1, 2])
    with col_t:
        st.session_state.title = st.text_input("Survey Title", value=st.session_state.title)
    with col_i:
        st.session_state.introduction = st.text_area("Survey Introduction/Instructions", 
                                                    value=st.session_state.introduction, 
                                                    placeholder="Welcome to our survey! Please answer honestly...")

    st.divider()
    
    # ── Add Question Section ──
    st.write("### Add Question")
    q_text = st.text_input("Question Text")
    q_type = st.selectbox("Type", ["mcq", "text", "ranking", "likert", "image"])
    q_meta = {}

    # 1. MCQ
    if q_type == "mcq":
        st.caption("Define options and where they jump to (use 99 for 'End Survey')")
        if "temp_options" not in st.session_state:
            st.session_state.temp_options = [{"text": "", "skip": 0}] #maryam 
        
        for idx, opt in enumerate(st.session_state.temp_options):
            c1, c2 = st.columns([3, 1])
            opt["text"] = c1.text_input(f"Option {idx+1}", value=opt["text"], key=f"opt_txt_{idx}")
            opt["skip"] = c2.number_input(f"Skip to Q#", value=opt["skip"], key=f"opt_skp_{idx}")
        
        if st.button("➕ Add Option"):
            st.session_state.temp_options.append({"text": "", "skip": 0})
            st.rerun()
        q_meta["options"] = st.session_state.temp_options

    # 2. Ranking (Updated to match Likert style setup)
    elif q_type == "ranking":
        num_items = st.slider("How many items to rank?", 2, 5, 3)
        q_meta["items"] = []
        st.write("Define items to be ranked:")
        cols = st.columns(num_items)
        for i in range(num_items):
            item_val = cols[i].text_input(f"Item {i+1}", key=f"rank_setup_{i}")
            q_meta["items"].append(item_val)

    # 3. Likert
    elif q_type == "likert":
        scale = st.slider("Scale size", 3, 6, 5)
        q_meta["scale"] = scale
        q_meta["labels"] = {}
        st.write("Define Labels (e.g., 1=Poor, 5=Excellent)")
        cols = st.columns(scale)
        for i in range(scale):
            q_meta["labels"][str(i+1)] = cols[i].text_input(f"Label {i+1}", key=f"lik_lbl_{i}")

    # 4. Text
    elif q_type == "text":
        q_meta["word_limit"] = st.number_input("Word Limit", min_value=1, max_value=500, value=150)

    # 5. Image
    elif q_type == "image":
        q_meta["image_url"] = st.text_input("Image URL")

    if st.button("Add Question to Survey"):
        if q_text:
            st.session_state.questions.append({"text": q_text, "type": q_type, "meta": q_meta})
            # Clean up temp state
            if "temp_options" in st.session_state: del st.session_state.temp_options
            st.rerun()

    st.divider()
    
    # ── Preview Section ──
    st.write("### Live Preview")
    if st.session_state.introduction:
        st.info(st.session_state.introduction)

    for i, q in enumerate(st.session_state.questions):
        st.markdown(f"**{i+1}. {q['text']}**")
        
        if q["type"] == "mcq":
            opts = [o["text"] for o in q["meta"].get("options", [])]
            choice = st.radio("Select", opts, key=f"p_{i}")

        elif q["type"] == "ranking":
            items = q["meta"].get("items", [])
            for idx, item in enumerate(items):
                st.selectbox(f"Rank {idx+1}:", ["--Select--"] + items, key=f"p_rank_{i}_{idx}")

        elif q["type"] == "likert":
            labels = q["meta"].get("labels", {})
            scale_size = q["meta"].get("scale", 3)
            cols = st.columns(scale_size)
            for j in range(scale_size):
                lbl = labels.get(str(j+1), "")
                cols[j].button(f"{j+1}\n{lbl}", key=f"l_{i}_{j}", use_container_width=True)

        elif q["type"] == "text":
            limit = q["meta"].get("word_limit", 150)
            st.text_area(f"Answer box (Limit: {limit} words)", key=f"t_{i}")

        elif q["type"] == "image":
            if q["meta"].get("image_url"): st.image(q["meta"]["image_url"])

    st.divider()
    col_save, col_back = st.columns(2)
    if col_save.button("💾 Save to Database", use_container_width=True):
        save_survey_to_db(st.session_state.title, st.session_state.introduction, st.session_state.questions)
        st.success("Survey, Introduction, and Logic saved!")
    
    if col_back.button("⬅ Back to Menu", use_container_width=True):
        st.session_state.mode = "list"
        st.rerun()
