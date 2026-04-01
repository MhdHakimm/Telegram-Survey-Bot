"""
Streamlit Dashboard — Survey Results Viewer
Run with:  streamlit run app.py
"""

import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from sheets_reader import get_responses_df

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Survey Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 1rem 1.5rem;
        text-align: center;
    }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# ── Title ─────────────────────────────────────────────────────────────────────
st.title("📊 Survey Dashboard")
st.caption("Live results from your Telegram Survey Bot")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Loading responses from Google Sheets…"):
    try:
        df = get_responses_df()
    except RuntimeError as err:
        st.error(str(err))
        st.info("Make sure your Google credentials file is configured in the `.env` file.")
        st.stop()

if df.empty:
    st.info("📭 No survey responses have been recorded yet.")
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("🔍 Filters")

all_surveys = sorted(df["Survey Title"].dropna().unique().tolist())
survey_choice = st.sidebar.selectbox("Survey", ["All Surveys"] + all_surveys)

# Date filter (only if Timestamp column is valid)
if "Timestamp" in df.columns and df["Timestamp"].notna().any():
    min_date = df["Timestamp"].min().date()
    max_date = df["Timestamp"].max().date()
    date_range = st.sidebar.date_input("Date range", [min_date, max_date])
    if len(date_range) == 2:
        df = df[
            (df["Timestamp"].dt.date >= date_range[0]) &
            (df["Timestamp"].dt.date <= date_range[1])
        ]

filtered = df if survey_choice == "All Surveys" else df[df["Survey Title"] == survey_choice]

# ── Top metrics ───────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("👥 Respondents",   filtered["User ID"].nunique())
c2.metric("📋 Surveys",       filtered["Survey Title"].nunique())
c3.metric("❓ Questions",      filtered["Question Text"].nunique())
c4.metric("✅ Total Answers",  len(filtered))

st.divider()

# ── All-surveys overview ──────────────────────────────────────────────────────
if survey_choice == "All Surveys":
    st.subheader("📋 Survey Overview")

    summary = (
        filtered.groupby("Survey Title")
        .agg(Respondents=("User ID", "nunique"), Answers=("Answer", "count"))
        .reset_index()
    )
    st.dataframe(summary, use_container_width=True, hide_index=True)

    fig = px.bar(
        summary, x="Survey Title", y="Respondents",
        color="Survey Title", title="Respondents per Survey",
        labels={"Survey Title": "Survey"},
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ── Per-survey deep dive ──────────────────────────────────────────────────────
else:
    st.subheader(f"📊 {survey_choice}")

    # Respondents over time
    if "Timestamp" in filtered.columns and filtered["Timestamp"].notna().any():
        time_df = (
            filtered.drop_duplicates(subset=["User ID"])
            .set_index("Timestamp")
            .resample("D")["User ID"].nunique()
            .reset_index()
            .rename(columns={"User ID": "New Respondents"})
        )
        fig_time = px.line(
            time_df, x="Timestamp", y="New Respondents",
            title="Daily Respondents", markers=True,
        )
        st.plotly_chart(fig_time, use_container_width=True)

    st.divider()

    # Per-question visualisation
    questions_ordered = (
        filtered[["Question #", "Question Text", "Question Type"]]
        .drop_duplicates()
        .sort_values("Question #")
    )

    for _, qrow in questions_ordered.iterrows():
        q_text = qrow["Question Text"]
        qtype  = qrow["Question Type"]
        q_df   = filtered[filtered["Question Text"] == q_text].copy()

        st.markdown(f"### Q{int(qrow['Question #'])}. {q_text}")
        st.caption(f"Type: **{qtype.replace('_', ' ').title()}** &nbsp;|&nbsp; Responses: **{len(q_df)}**")

        # ── Likert ────────────────────────────────────────────────────────────
        if qtype == "likert":
            q_df["Score"] = q_df["Answer"].str.extract(r"^(\d)").astype(float)

            col_bar, col_gauge = st.columns(2)

            with col_bar:
                counts = q_df["Answer"].value_counts().reset_index()
                counts.columns = ["Answer", "Count"]
                counts = counts.sort_values("Answer")
                fig_bar = px.bar(
                    counts, x="Answer", y="Count",
                    color="Answer", title="Response Distribution",
                )
                fig_bar.update_layout(showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)

            with col_gauge:
                avg = q_df["Score"].mean()
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=round(avg, 2),
                    delta={"reference": 3, "increasing": {"color": "green"}},
                    title={"text": "Average Score"},
                    gauge={
                        "axis": {"range": [1, 5]},
                        "bar": {"color": "#4C72B0"},
                        "steps": [
                            {"range": [1, 2], "color": "#ff6b6b"},
                            {"range": [2, 4], "color": "#ffd93d"},
                            {"range": [4, 5], "color": "#6bcb77"},
                        ],
                    },
                ))
                st.plotly_chart(fig_gauge, use_container_width=True)

        # ── Multiple choice ───────────────────────────────────────────────────
        elif qtype == "multiple_choice":
            counts = q_df["Answer"].value_counts().reset_index()
            counts.columns = ["Option", "Count"]

            col_bar, col_pie = st.columns(2)
            with col_bar:
                fig_bar = px.bar(
                    counts, x="Option", y="Count",
                    color="Option", title="Response Distribution",
                )
                fig_bar.update_layout(showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)
            with col_pie:
                fig_pie = px.pie(counts, names="Option", values="Count", title="Share")
                st.plotly_chart(fig_pie, use_container_width=True)

        # ── Ranking ───────────────────────────────────────────────────────────
        elif qtype == "ranking":
            all_ranks: dict[str, list[int]] = {}
            for answer in q_df["Answer"]:
                # Expected format: "1. Option A → 2. Option B → 3. Option C"
                items = re.findall(r"\d+\.\s*(.+?)(?:\s*→|$)", answer)
                for rank, item in enumerate(items, start=1):
                    item = item.strip()
                    all_ranks.setdefault(item, []).append(rank)

            if all_ranks:
                rank_df = pd.DataFrame([
                    {
                        "Option":    k,
                        "Avg Rank":  round(sum(v) / len(v), 2),
                        "# Ranked":  len(v),
                    }
                    for k, v in all_ranks.items()
                ]).sort_values("Avg Rank")

                fig_rank = px.bar(
                    rank_df, x="Option", y="Avg Rank",
                    color="Option",
                    title="Average Rank (lower = more preferred)",
                    text="Avg Rank",
                )
                fig_rank.update_layout(showlegend=False, yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_rank, use_container_width=True)
                st.dataframe(rank_df, use_container_width=True, hide_index=True)

        st.divider()

# ── Raw data & export ─────────────────────────────────────────────────────────
with st.expander("📄 Raw Response Data"):
    display_df = filtered.copy()
    if "Timestamp" in display_df.columns:
        display_df["Timestamp"] = display_df["Timestamp"].astype(str)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    csv_data = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download as CSV",
        data=csv_data,
        file_name="survey_responses.csv",
        mime="text/csv",
    )
