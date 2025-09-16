# To clean, transform, and package raw data retrieved from postgresql and chromadb
import pandas as pd # Manage and transform tabular data into DataFrames. This simplifies cleaning and graphing.
from typing import Dict, Any

class Preprocessor:
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if input_data["source"] == "postgres":
            return self._process_postgres_data(
                raw_data=input_data["data"],
                filters=input_data.get("filters", {})
            ) # We clean up the structured rows(e.g., ensure the timestamps are parsed, handle NaNs.)
        elif input_data["source"] == "chromadb":
            return self._process_vector_data(input_data["data"]) # We combine matched text chunks into one blob for display.
        else:
            return {"df": None, "source": input_data["source"]} # Failsafe return, prevents crashes.

    def _process_postgres_data(self, raw_data: list, filters: Dict[str, Any]) -> Dict[str, Any]:
        df = pd.DataFrame(raw_data) # Converts list of dicts into pandas dataframe for easy manipulation and graphing.

        # Convert timestamp columns
        for col in ["start_time", "end_time"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]) # Ensure timestamp columns are correctly parsed as datetime objects

        df = df.drop_duplicates() # Remove duplicate rows
        df.fillna(0, inplace=True) # Replace any NaNs

        # Continuous high-value check (if requested)
        if filters.get("require_continuous_check"):
            print("Computing continuous high-value streaks...")

            threshold = 800 if "co2" in filters.get("metric_name", []) else 21 if "temp" in filters.get("metric_name", []) else None

            if threshold is not None:
                df["is_high"] = df["value"] > threshold

                # Identify streaks per room
                df["continuous_high_count"] = 0
                for (room, gid), group in df.groupby(["Room_Name", "geometry_id"]):
                    streaks = (group["is_high"] != group["is_high"].shift()).cumsum()
                    high_streaks = group[group["is_high"]].groupby(streaks)["is_high"].transform("count")
                    df.loc[group.index, "continuous_high_count"] = high_streaks.fillna(0)

                print("continuous_high_count column added")

        return {"df": df, "source": "postgres", "filters": filters}

    def _process_vector_data(self, documents: list) -> Dict[str, Any]:
        combined = "\n\n".join(documents) # Combine matched text chunks into a single string blob.
        return {"df": None, "source": "chromadb", "text": combined}
