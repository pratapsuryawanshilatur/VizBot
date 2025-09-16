from typing import Dict, Any
from llm.openai_connector import get_llm
from langchain_core.prompts import ChatPromptTemplate
import json
import re
from datetime import datetime, timedelta

llm = get_llm()

FILTER_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You extract filters from user queries and return JSON like:\n"
        "{{{{\n"
        "  \"rooms\": [\"Seminar-64\", \"Lecture Theatre-4\"],\n"
        "  \"floor\": [1],\n"
        "  \"area\": [\"sbs\"],\n"
        "  \"date_range\": [\"2025-06-15\", \"2025-06-21\"],\n"
        "  \"is_holiday\": false,\n"
        "  \"is_working\": true,\n"
        "  \"metric_name\": [\"co2\", \"humidity\"],\n"
        "  \"require_continuous_check\": true,\n"
        "  \"aggregation\": \"max\",\n"
        "  \"limit\": 5\n"
        "}}}}\n"
        "Use 'aggregation' if query uses: highest, lowest, most, least, top, max, min, average.\n"
        "If user says \"busiest\" or \"most occupied\", set metric_name = [\"Occupancy\"].\n"
        "Date format: YYYY-MM-DD. If no filter, return empty list or null (for booleans)."
    ),
    ("human", "{input}")
])

class FilterExtractor:
    def invoke(self, user_query: str) -> Dict[str, Any]:
        print("User query sent to FilterExtractor:", user_query)
        chain = FILTER_PROMPT | llm

        try:
            result = chain.invoke({"input": user_query})
            parsed = json.loads(result.content)
            if not parsed.get("metric_name"):
                print("LLM did not extract metric_name. Falling back to regex.")
                parsed = self._fallback_extract(user_query)
        except Exception as e:
            print(f"LLM extraction failed ({e}). Falling back to regex.")
            parsed = self._fallback_extract(user_query)

        new_filters = self._normalize_filters(parsed)
        print("Extracted filters:", new_filters)
        return new_filters

    def _normalize_filters(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        alias_map = {
            "temperature": "temp",
            "co₂": "co2",
            "co_2": "co2",
            "humid": "humidity",
            "occupants": "Occupancy",
            "people": "Occupancy",
            "air quality": "co2",
            "busiest": "Occupancy"
        }

        filters = {
            "rooms": raw.get("rooms") if isinstance(raw.get("rooms"), list) else [],
            "floor": raw.get("floor") if isinstance(raw.get("floor"), list) else [],
            "area": raw.get("area") if isinstance(raw.get("area"), list) else [],
            "date_range": raw.get("date_range") if isinstance(raw.get("date_range"), list) else [],
            "is_holiday": raw.get("is_holiday") if raw.get("is_holiday") in [True, False, None] else None,
            "is_working": raw.get("is_working") if raw.get("is_working") in [True, False, None] else None,
            "require_continuous_check": bool(raw.get("require_continuous_check", False)),
            "aggregation": raw.get("aggregation") if raw.get("aggregation") in ["max", "min", "avg", "sum", None] else None,
            "limit": raw.get("limit") if isinstance(raw.get("limit"), int) else None
        }

        metric_names = raw.get("metric_name", [])
        if not isinstance(metric_names, list):
            metric_names = []

        filters["metric_name"] = [alias_map.get(m.lower(), m) for m in metric_names]
        return filters

    def _fallback_extract(self, query: str) -> Dict[str, Any]:
        rooms = re.findall(r"(Seminar[-\s]?\d+|Library|Lecture Theatre-\d+|Café|Dining-room|Founders-room|Reception|Rhodes-Trust|Nelson-Mandela|Edmund-Safra)", query, re.I)
        floors = [int(f) for f in re.findall(r"floor[- ]?(\d+)", query, re.I)]
        areas = re.findall(r"(sbs)", query, re.I)

        date_range = []
        today = datetime.today()
        if "last week" in query.lower():
            date_range = [
                (today - timedelta(days=7)).strftime("%Y-%m-%d"),
                today.strftime("%Y-%m-%d")
            ]

        is_holiday = True if "holiday" in query.lower() else None
        is_working = True if "working day" in query.lower() else None

        metric_keywords = [
            "batteryLevel", "cloudcover", "co2", "daysToMold", "equilibriumMoistureContent",
            "extHumidity", "extTemp", "feelslike", "humidity", "inCount", "inCountTotal",
            "mechanicalDamage", "metalCorrosion", "Occupancy", "outCount", "outCountTotal",
            "peopleCount", "peopleMotion", "peopleMotionTotal", "precip", "preservationIndex",
            "temp", "winddir", "windgust", "windspeed"
        ]
        metric_name = [m for m in metric_keywords if re.search(rf"\b{re.escape(m)}\b", query, re.I)]

        if not metric_name:
            fallback_map = {
                "hottest": "temp",
                "cold": "temp",
                "humid": "humidity",
                "busiest": "Occupancy",
                "busy": "Occupancy",
                "occupied": "Occupancy",
                "dry": "humidity",
                "co2": "co2",
                "air quality": "co2"
            }
            for k, v in fallback_map.items():
                if re.search(rf"\b{re.escape(k)}\b", query, re.I):
                    metric_name = [v]
                    break

        require_continuous = bool(re.search(r"\b(continuous|persistently|consistently|constantly|sustained|prolonged)\b", query, re.I))

        aggregation = None
        if re.search(r"\b(highest|max|most|busiest|hottest|top)\b", query, re.I):
            aggregation = "max"
        elif re.search(r"\b(lowest|min|least|coldest)\b", query, re.I):
            aggregation = "min"
        elif re.search(r"\b(average|avg|typical)\b", query, re.I):
            aggregation = "avg"
        elif re.search(r"\b(sum|total)\b", query, re.I):
            aggregation = "sum"

        limit_match = re.search(r'\b(?:top|bottom)?\s*(\d+)\b', query, re.I)
        limit = int(limit_match.group(1)) if limit_match else None

        return {
            "rooms": [r.strip() for r in rooms],
            "floor": floors,
            "area": [a.strip() for a in areas],
            "date_range": date_range,
            "is_holiday": is_holiday,
            "is_working": is_working,
            "metric_name": metric_name,
            "require_continuous_check": require_continuous,
            "aggregation": aggregation,
            "limit": limit
        }
