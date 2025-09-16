# This file handles data retrieval for both postgresql database and chromadb vector store
from sqlalchemy import create_engine, text # Use sqlalchemy to connect to and run queries on the postgres database
from sqlalchemy.orm import sessionmaker
from database.models import SpaceMetadata, SpaceUsage # provide db schema references from models.py
import os # for env vars, paths
from dotenv import load_dotenv # loads DB URL and configs from .env.
from typing import Dict, Any
from datetime import datetime
import streamlit as st

# Load env variables
load_dotenv() # pulls our environment variables

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session() # allows us to execute SQL statements on DB.

class DataRetriever:
    def run(self, input_data: Dict[str, Any], filters: Dict[str, Any] = None) -> Dict[str, Any]:
        intent = input_data["intent"]
        query = input_data["query"]

        # Routes query to DB or vector search based on intent.
        if intent in ["generate_graph", "insight_request"]:
            return self._query_postgres(filters)

        elif intent in ["rag_query", "upload_ocr"]:
            return self._query_vector_store(query)
        
        return {"data": None, "source": "unknown"}

    def _query_postgres(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        if filters is None:
            filters = st.session_state.get("partial_filters", {})
        # --- Build geometry_id list based on metadata filters ---
        geom_where = []
        geom_params = {}

        if filters:
            #Applies room name filters if provided
            if filters.get("rooms"):
                geom_where.append('m."Room_Name" ILIKE ANY(:rooms)')
                geom_params["rooms"] = [f"%{r}%" for r in filters["rooms"]]

            # Applies floor filters if provided
            if filters.get("floor"):
                geom_where.append('m."Floor" = ANY(:floors)')
                geom_params["floors"] = filters["floor"]

            # Applies area filters if provided
            if filters.get("area"):
                geom_where.append('m."Area" ILIKE ANY(:areas)')
                geom_params["areas"] = [f"%{a}%" for a in filters["area"]]

        # Fetch geometry IDs matching filters, needed for next usage query.
        geom_sql = f'SELECT m.geometry_id, m."Room_Name" FROM space_metadata m {"WHERE " + " AND ".join(geom_where) if geom_where else ""}'
        geom_result = session.execute(text(geom_sql), geom_params)
        geom_data = geom_result.fetchall()
        geometry_ids = [row.geometry_id for row in geom_data]
        #room_map = {row.geometry_id: row.Room Name for row in geom_data}

        # Early exit if no match 
        if not geometry_ids:
            print("No geometry IDs matched metadata filters.")
            return {"data": [], "source": "postgres"}

        # --- Build main usage query ---
        usage_where = ['u.geometry_id = ANY(:geometry_ids)']
        usage_params = {"geometry_ids": geometry_ids}

        if filters:
            if len(filters.get("date_range", [])) == 2:
                usage_where.append("u.start_time BETWEEN :start_date AND :end_date")
                usage_params["start_date"] = f"{filters['date_range'][0]} 00:00:00"
                usage_params["end_date"] = f"{filters['date_range'][1]} 23:59:59"

            if filters.get("is_holiday") is not None:
                usage_where.append("u.is_holiday = :is_holiday")
                usage_params["is_holiday"] = filters["is_holiday"]

            if filters.get("is_working") is not None:
                usage_where.append("u.is_working = :is_working")
                usage_params["is_working"] = filters["is_working"]

            if filters.get("metric_name"):
                usage_where.append("u.metric_name = ANY(:metric_names)")
                usage_params["metric_names"] = filters["metric_name"]

        # AGGREGATED QUERY
        if filters.get("aggregation") and filters.get("metric_name") and not filters.get("rooms"):
            agg_func = filters["aggregation"]
            limit = filters.get("limit", 1)
            agg_sql = f"""
                SELECT m."Room_Name", m."Floor", m."Area", u.metric_name, {agg_func}(u.value) AS value
                FROM space_usage u
                JOIN space_metadata m ON u.geometry_id = m.geometry_id
                WHERE {' AND '.join(usage_where)}
                GROUP BY m."Room_Name", m."Floor", m."Area", u.metric_name
                ORDER BY value {"DESC" if agg_func in ["max", "sum"] else "ASC"}
                LIMIT {limit}
            """
            print("Aggregation Query:", agg_sql)
            print("Params:", usage_params)

            result = session.execute(text(agg_sql), usage_params)
            top_rows = result.mappings().all()

            if not top_rows:
                return {"data": [], "source": "postgres"}

            # Extract top room name and re-query full data for it
            top_rooms = [row["Room_Name"] for row in top_rows]
            print("Top room by aggregation:", top_rooms)

            filters["rooms"] = top_rooms  # Add top room into filters
            filters["aggregation"] = None  # Clear aggregation to avoid second aggregation
            filters["limit"] = None        # Clear limit for next query

            # Recurse to fetch full data
            return self._query_postgres(filters)

        # CONTINUOUS CHECK HANDLING
        if filters.get("require_continuous_check") and not filters.get("aggregation") and not filters.get("limit"):
            # Safe metric fallback
            metric_list = filters.get("metric_name", [])
            metric = metric_list[0] if metric_list else "co2"
            threshold_map = {
                "co2": 1000,
                "Occupancy": 100,
                "humidity": 70,
                "temp": 27
            }
            threshold = threshold_map.get(metric, 1000)

            continuous_sql = f"""
                SELECT m."Room_Name", u.geometry_id, u.metric_name,
                    COUNT(*) FILTER (WHERE u.value > {threshold}) AS continuous_high_count
                FROM space_usage u
                JOIN space_metadata m ON u.geometry_id = m.geometry_id
                WHERE {' AND '.join(usage_where)} AND u.metric_name = :metric
                GROUP BY m."Room_Name", u.geometry_id, u.metric_name
                ORDER BY continuous_high_count DESC
            """
            usage_params["metric"] = metric
            print("Continuous high metric SQL:", continuous_sql)

            result = session.execute(text(continuous_sql), usage_params)
            top_rows = result.mappings().all()
            #rows = result.fetchall()
            #columns = result.keys()
            #data = [dict(zip(columns, row)) for row in rows]

            if not top_rows:
                return {"data": [], "source": "postgres"}

            #return {"data": data, "source": "postgres", "download": None}
            top_geometry_ids = [row["geometry_id"] for row in top_rows]
            top_room_names = [row["Room_Name"] for row in top_rows]

            # Prepare filters for full re-query
            filters["rooms"] = top_room_names
            filters["require_continuous_check"] = False
            filters["aggregation"] = None
            filters["limit"] = None

            return self._query_postgres(filters)

        # --- Regular usage query (unchanged)
        usage_sql = f"""
            SELECT u.*, m."Area", m."Floor", m."Room_Name"
            FROM space_usage u
            JOIN space_metadata m ON u.geometry_id = m.geometry_id
            WHERE {' AND '.join(usage_where)}
        """
        
        print("Final SQL Query:", usage_sql)
        print("SQL Params:", usage_params)

        result = session.execute(text(usage_sql), usage_params)
        rows = result.fetchall()
        columns = result.keys()
        data = [dict(zip(columns, row)) for row in rows] # Converts DB rows into list of dicts for easy graphing and download.
        print(f"Rows returned: {len(data)}")

        # Save to CSV for download button
        download_path = "data/filtered_results.csv"
        if data:
            import pandas as pd
            pd.DataFrame(data).to_csv(download_path, index=False)

        return {"data": data, "source": "postgres", "download": download_path}

    """


    def _query_vector_store(self, query: str) -> Dict[str, Any]:
        embedding = embedding_model.encode(query).tolist() # Generates embedding for user query
        results = collection.query(query_embeddings=[embedding], n_results=3) # gets top 3 closest matches from vector DB.
        matches = results.get("documents", [[]])[0] # Log matches
        print(f"ChromaDB matches: {matches}") # returns the text chunks matched.
        return {"data": matches, "source": "chromadb"}

    """
