"""
Agent to classify user intent: generate a graph or run OCR+RAG based on query or uploaded file.
Also determines if query is incomplete using heuristics.
"""

import streamlit as st
from llm.openai_connector import get_llm
from langchain_core.runnables import Runnable
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any

llm = get_llm()

INTENT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an intelligent intent classifier. Given a user's query, classify it as one of the following intents:\n"
        "- generate_graph: if the user is asking to visualize structured data (trends, usage, time series, comparisons)\n"
        "- ocr+rag_intent: user uploads file to extract + retrieve text insights.\n\n"
        "Only return one of these: generate_graph or ocr+rag_intent.\n\n"
        "Examples:\n"
        "Query: 'Show occupancy data of Seminar-51 from last week' -> generate_graph\n"
        "Query: 'Graph the humidity in all rooms during May' -> generate_graph\n"
        "Query: 'What’s the average temperature in Library this week?' -> generate_graph\n"
        "Query: 'Compare temperature and CO2 levels for Lecture Theatre-4' -> generate_graph\n"
        "Query: 'Plot CO2 and humidity levels for Seminar-20 last Monday' -> generate_graph\n"
        "Query: 'Rooms with continuous high CO2 levels ordered by worst' -> generate_graph\n"
        "Query: 'Which room has the highest CO2 today?' -> generate_graph\n"
        "Query: 'Hottest room right now?' -> generate_graph\n"
        "Query: 'Top 1 Occupancy room' -> generate_graph\n"
        "Query: 'Top 5 Occupancy room this month' -> generate_graph\n"
        "Query: 'Most occupied area on Monday?' -> generate_graph\n"
        "Query: 'Here’s a scanned maintenance report — extract insights' -> ocr+rag_intent\n"
        "Query: 'Upload and analyze this room blueprint PDF' -> ocr+rag_intent"
    ),
    ("human", "User Input:\n{input}")
])

def is_query_incomplete(text: str) -> Dict[str, bool]:
    """Check if the query is missing critical info (date range or metric)."""
    text = text.lower()
    missing = {"date_range_missing": False, "metric_missing": False}

    if not any(t in text for t in [
        "week", "month", "today", "yesterday", "june", "april", "monday",
        "from", "between", "day", "date", "range"
    ]):
        missing["date_range_missing"] = True

    if not any(m in text for m in [
        "co2", "occupancy", "temperature", "humidity", "utilization", "value", "metric"
    ]):
        missing["metric_missing"] = True

    return missing

class QueryPlanner(Runnable):
    def invoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Plan query execution: only generate_graph intent now."""
        user_input = input_data.get("content", "")
        input_type = input_data.get("type", "text")

        # Direct LLM call for future flexibility (always returns generate_graph)
        try:
            result = (INTENT_PROMPT | llm).invoke({"input": user_input})
            intent = result.content.strip().lower()
        except Exception:
            intent = "generate_graph"  # fallback

        # Force to generate_graph (OCR removed)
        intent = "generate_graph"

        # Heuristic check for missing filters
        missing = {}
        heuristic_missing = is_query_incomplete(user_input)

        if heuristic_missing["date_range_missing"]:
            missing["date_range"] = True
        if heuristic_missing["metric_missing"]:
            missing["metric_name"] = True

        return {
            "intent": intent,
            "query": user_input,
            "input_type": input_type,
            "missing": missing
        }