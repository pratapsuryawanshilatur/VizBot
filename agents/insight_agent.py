# Generates the natural-language insights based on the processed data(e.g., trends, patterns).
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from llm.openai_connector import get_llm

llm = get_llm()

INSIGHT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You generate a detailed, meaningful and professional insight summary strictly based on the provided data summary and graph. "
        "Explicitly mention the metric name being analyzed (e.g., CO2, Temperature, Occupancy).\n"
        "Identify trends, peaks, anomalies, sustained behaviors, and room comparisons directly from the statistics.\n"
        "If any aggregation pattern is obvious (like highest, lowest, average), reflect that clearly in the insight.\n"
        "The insight should reflect the actual values, ranges, and comparisons present in the data. Base your insights strictly on the data provided."
        "Give suggestion on the basis of data and what could be the best for the scenario."
        "Do not hallucinate or mention things not in the data."
    ),
    ("human", "{input}")
])

class InsightAgent:
    def invoke(self, processed_data: Dict[str, Any], user_query: str = None) -> Dict[str, Any]:
        df = processed_data.get("df")

        if df is None or df.empty:
            return {"insights": "No data available to generate insights."}

        summary_lines = []

        # Handle pre-aggregated top-N summary (short tables with only one row per room)
        if (
            "Room_Name" in df.columns
            and "metric_name" in df.columns
            and "value" in df.columns
            and df["Room_Name"].nunique() == len(df)
            and df["start_time"].nunique() <= 1
        ):
            for idx, row in df.iterrows():
                room = row["Room_Name"]
                metric = row["metric_name"].upper()
                val = row["value"]
                summary_lines.append(f"🔹 {room} has {metric} value: {val:.2f}")

        # --- MULTI-METRIC DETAILED ANALYSIS ---

        elif "metric_name" in df.columns and df["metric_name"].nunique() > 1:
            for metric in df["metric_name"].unique():
                metric_df = df[df["metric_name"] == metric]
                summary_lines.append(f"\n🔹 Metric: {metric}")

                agg_notes = []

                if "value" in metric_df.columns and not metric_df["value"].empty:
                    min_val = metric_df["value"].min()
                    max_val = metric_df["value"].max()
                    avg_val = metric_df["value"].mean()
                    summary_lines.append(f"  - Min: {min_val:.2f}, Max: {max_val:.2f}, Avg: {avg_val:.2f}")

                    try:
                        if max_val == metric_df["value"].iloc[metric_df["value"].idxmax()]:
                            agg_notes.append("max")
                        if min_val == metric_df["value"].iloc[metric_df["value"].idxmin()]:
                            agg_notes.append("min")
                    except Exception:
                        pass  # Safeguard if idxmax/min fails

                    if agg_notes:
                        summary_lines.append(f"  - Aggregation detected: {', '.join(agg_notes)}")

                if "continuous_high_count" in metric_df.columns:
                    max_streak = metric_df["continuous_high_count"].max()
                    avg_streak = metric_df["continuous_high_count"].mean()
                    summary_lines.append(f"  - Max continuous high count: {max_streak}, Avg streak: {avg_streak:.2f}")

                if "Room_Name" in metric_df.columns:
                    room_stats = metric_df.groupby("Room_Name")["value"].mean().to_dict()
                    room_summaries = [f"{room}: avg {val:.2f}" for room, val in room_stats.items()]
                    summary_lines.append("  - Room-wise Avg: " + ", ".join(room_summaries))

                if "hour" in metric_df.columns and not metric_df["hour"].empty:
                    peak_hour = metric_df.groupby("hour")["value"].mean().idxmax()
                    summary_lines.append(f"  - Peak Hour: {peak_hour}")

                if "dayofweek" in metric_df.columns and not metric_df["dayofweek"].empty:
                    peak_day = metric_df.groupby("dayofweek")["value"].mean().idxmax()
                    summary_lines.append(f"  - Peak Day (0=Mon): {peak_day}")

        # --- SINGLE METRIC / TIME SERIES ---

        else:
            metric_label = "Metric"
            if "metric_name" in df.columns and df["metric_name"].nunique() == 1:
                metric_label = df["metric_name"].unique()[0].upper()
                summary_lines.append(f"\n🔹 Metric: {metric_label}")

            agg_notes = []

            if "value" in df.columns and not df["value"].empty:
                min_val = df["value"].min()
                max_val = df["value"].max()
                avg_val = df["value"].mean()
                summary_lines.append(f"{metric_label} - Min: {min_val:.2f}, Max: {max_val:.2f}, Avg: {avg_val:.2f}")

                try:
                    if max_val == df["value"].iloc[df["value"].idxmax()]:
                        agg_notes.append("max")
                    if min_val == df["value"].iloc[df["value"].idxmin()]:
                        agg_notes.append("min")
                except Exception:
                    pass

                if agg_notes:
                    summary_lines.append(f"Aggregation detected: {', '.join(agg_notes)}")

            if "continuous_high_count" in df.columns:
                max_streak = df["continuous_high_count"].max()
                avg_streak = df["continuous_high_count"].mean()
                summary_lines.append(f"Maximum continuous high streak: {max_streak}")
                summary_lines.append(f"Average continuous high streak: {avg_streak:.2f}")

            if "Room_Name" in df.columns:
                room_stats = df.groupby("Room_Name")["value"].mean().to_dict()
                room_summaries = [f"{room}: avg {val:.2f}" for room, val in room_stats.items()]
                summary_lines.append("Room-wise average utilization: " + ", ".join(room_summaries))

            if "hour" in df.columns and not df["hour"].empty:
                peak_hour = df.groupby("hour")["value"].mean().idxmax()
                summary_lines.append(f"Peak usage hour (avg): {peak_hour}")

            if "dayofweek" in df.columns and not df["dayofweek"].empty:
                peak_day = df.groupby("dayofweek")["value"].mean().idxmax()
                summary_lines.append(f"Peak usage dayofweek (0=Mon): {peak_day}")

        summary_text = "\n".join(summary_lines)

        final_prompt = f"""User asked: "{user_query}"\n\n{summary_text}""" if user_query else summary_text

        print("Data summary for insight generation:\n", final_prompt)

        chain = INSIGHT_PROMPT | llm
        result = chain.invoke({"input": final_prompt})

        insight = result.content.strip()
        return {"insights": insight}
