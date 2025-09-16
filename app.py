# Heart of the application

import streamlit as st
import streamlit_authenticator as stauth
import plotly.graph_objects as go
from utils.auth_utils import verify_user
from agents.query_planner import QueryPlanner
from agents.data_retriever import DataRetriever
from agents.preprocessor import Preprocessor
from agents.graph_generator import GraphGenerator
from agents.insight_agent import InsightAgent
from agents.output_agent import OutputAgent
from agents.filter_extractor import FilterExtractor
import os
import datetime
from streamlit_lottie import st_lottie
import json

# Keep LangSmith environment active
os.environ["LANGCHAIN_PROJECT"] = "vizbot"

# Page config
st.set_page_config(page_title="VizBot - Graphs & Insights", layout="wide")


# ---------------- Lottie Loader ----------------
def load_lottiefile(filepath: str):
    with open(filepath, "r") as f:
        return json.load(f)


lottie_animation = load_lottiefile("data/animation/office_workflow4.json")


# ---------------- Sidebar Login ----------------
st.sidebar.title("📱 Login")
authenticator = stauth.Authenticate(
    credentials={"usernames": {}},
    cookie_name="smartviz_cookie",
    key="random_key",
    cookie_expiry_days=1
)
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")
login_btn = st.sidebar.button("Login")

if login_btn:
    if verify_user(username, password):
        st.session_state["user"] = username
        st.success(f"🤝Welcome, {username}!")
    else:
        st.error("Invalid credentials")

if "user" not in st.session_state:
    st.stop()

# ---------------- Session Variables ----------------
st.session_state.setdefault("chat_history", [])
st.session_state.setdefault("query", None)
st.session_state.setdefault("query_stage", "intent")
st.session_state.setdefault("intent", None)
st.session_state.setdefault("partial_filters", {})

# ---------------- Chatbot Header ----------------
st.markdown(
    "<h1 style='text-align:center;'>Welcome to <span style='color:#6A5ACD'>VizBot</span> 📈🔭</h1>",
    unsafe_allow_html=True
)
st_lottie(lottie_animation, speed=1, height=300, key="welcome")


# ---------------- Chat Input ----------------
user_input = st.chat_input("Ask your query (e.g., Show CO2 trend in Seminar-51)")

if user_input:
    st.chat_message("user").markdown(user_input)

    if st.session_state.query_stage == "intent":
        st.session_state.query = user_input
        planned = QueryPlanner().invoke({
            "content": user_input,
            "type": "text",
            "file_uploaded": False
        })
        st.session_state.intent = planned["intent"]

        # We removed OCR/RAG logic, only generate graph queries remain
        filters = FilterExtractor().invoke(user_input)
        st.session_state.partial_filters.update(filters)

        # Determine missing filters
        missing_filters = []
        if not st.session_state.partial_filters.get("date_range"):
            missing_filters.append("date_range")
        if not st.session_state.partial_filters.get("graph_type"):
            missing_filters.append("graph_type")

        if not missing_filters:
            st.session_state.query_stage = "run"
        else:
            if "date_range" in missing_filters:
                st.chat_message("assistant").markdown(
                    "📅 Please specify the date range like `2025-07-01 to 2025-07-07`"
                )
                st.session_state.query_stage = "date"
            elif "graph_type" in missing_filters:
                st.chat_message("assistant").markdown(
                    "📊 What graph type would you like? (`line`, `bar`, `box`, or `heatmap`)"
                )
                st.session_state.query_stage = "graph_type"

    elif st.session_state.query_stage == "date":
        try:
            from_date, to_date = user_input.split(" to ")
            st.session_state.partial_filters["date_range"] = [from_date.strip(), to_date.strip()]
            if not st.session_state.partial_filters.get("graph_type"):
                st.chat_message("assistant").markdown(
                    "📊 What graph type would you like? (`line`, `bar`, `box`, or `heatmap`)"
                )
                st.session_state.query_stage = "graph_type"
            else:
                st.session_state.query_stage = "run"
        except:
            st.chat_message("assistant").markdown(
                "❗ Please enter date range like: `2025-07-01 to 2025-07-07`"
            )

    elif st.session_state.query_stage == "graph_type":
        graph_type = user_input.lower().strip()
        if graph_type in ["line", "bar", "box", "heatmap"]:
            st.session_state.partial_filters["graph_type"] = graph_type
            st.session_state.query_stage = "run"
        else:
            st.chat_message("assistant").markdown(
                "📊 Please enter a valid graph type: `line`, `bar`, `box`, or `heatmap`"
            )

# ---------------- Final Stage: Run Analysis ----------------
if st.session_state.query_stage == "run":
    with st.spinner("🔄 Running analysis..."):
        planned = {
            "intent": st.session_state.intent,
            "query": st.session_state.query,
            "input_type": "text"
        }

        # Main SQL data retrieval pipeline
        retrieved = DataRetriever().run(planned, filters=st.session_state.partial_filters)
        processed = Preprocessor().run(retrieved)
        st.session_state["last_filtered_df"] = processed.get("df")
        graphs = GraphGenerator().run(processed, graph_type=st.session_state.partial_filters.get("graph_type"))
        insights = InsightAgent().invoke(processed, user_query=st.session_state.query)
        output = OutputAgent().run({"graphs": graphs, "insights": insights["insights"]})

    # ----------- Display Graphs -----------
    st.subheader("📊 Visualizations")
    if output["graph_outputs"]:
        graph_info = output["graph_outputs"][0]
        fig = graph_info["fig"]

        if isinstance(fig, go.Figure) and fig.data and len(fig.data) > 0:
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(f"**{graph_info['title']}**")
        else:
            st.warning("📭 The graph was generated but contains no data.")
    else:
        st.warning("🚫 No graph output was generated.")

    # ----------- Display Insights -----------
    st.subheader("📌 Insights")
    st.markdown(output["insights"])

    # Save chat
    st.session_state.chat_history.append((st.session_state.query, output["insights"]))

    # Reset session for next query
    st.session_state.query_stage = "intent"
    st.session_state.query = None
    st.session_state.intent = None
    st.session_state.partial_filters = {}

    st.chat_message("assistant").markdown("💬 Ready for your next question!")


# ---------------- Sidebar ----------------
if st.session_state.chat_history:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🕒 Chat History")
    for i, (q, a) in enumerate(reversed(st.session_state.chat_history[-5:]), 1):
        st.sidebar.markdown(f"**{i}.** {q[:50]}...")

# Download Filtered Data (in sidebar)
if st.session_state.get("last_filtered_df") is not None:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📥 Download")
    csv = st.session_state["last_filtered_df"].to_csv(index=False).encode("utf-8")
    st.sidebar.download_button(
        label="Download Filtered Data (CSV)",
        data=csv,
        file_name="filtered_data.csv",
        mime="text/csv"
    )
