# This script sets up the database tables and loads CSV data into respective tables.
import pandas as pd
from sqlalchemy import create_engine # database engine
from sqlalchemy.orm import sessionmaker # ORM session management
from models import Base, SpaceMetadata, SpaceUsage  # Import DB tables and Base for table creation.
import os
from dotenv import load_dotenv

# Load env vars
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def create_tables():
    Base.metadata.create_all(engine) # Generate the DB table

def load_metadata(csv_path, session):
    # Read CSV file with encoding to handle special chars.
    df = pd.read_csv(csv_path, encoding="latin1")
    inserted = 0
    skipped = 0
    for _, row in df.iterrows():
        geometry_id = str(row["geometry_id"])
        existing = session.query(SpaceMetadata).filter_by(geometry_id=geometry_id).first() # Check if this geometry ID already exists -> skip duplicates.
        if existing:
            skipped += 1
            continue
        metadata = SpaceMetadata(
            Area=row.get("Area", ""),
            Floor=row.get("Floor"),
            Room_Name=row.get("Room Name", ""),
            geometry_id=geometry_id,
            parent_id=row.get("parent_id")
        )
        session.add(metadata)
        inserted += 1
    session.commit()
    print(f"Loaded metadata: {inserted} inserted, {skipped} skipped.")

def load_usage(csv_path, session):
    df = pd.read_csv(csv_path, encoding="latin1")
    #Ensure time columns are datetime type.
    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])

    valid_geometry_ids = {row[0] for row in session.query(SpaceMetadata.geometry_id).all()} # Get valid geometry IDs to validate usage table rows.

    skipped = 0
    inserted = 0

    for _, row in df.iterrows():
        if str(row["geometry_id"]) not in valid_geometry_ids:
            skipped += 1
            continue # Skip usage rows with invalid geometry IDs.
        usage = SpaceUsage(
            frequency=row.get("frequency"),
            start_time=row.get("start_time"),
            end_time=row.get("end_time"),
            metric_name=row.get("metric_name"),
            aggregation=row.get("aggregation"),
            value=row.get("value"),
            geometry_id=row.get("geometry_id"),
            is_holiday=bool(row.get("is_holiday")),
            is_valid=bool(row.get("is_valid")),
            is_working=bool(row.get("is_working")),
            hour=row.get("hour"),
            dayofweek=row.get("dayofweek"),
            month=row.get("month")
        )
        session.add(usage)
        inserted += 1
    session.commit()
    print(f"Loaded usage: {inserted} inserted, {skipped} skipped.")

# Allows this file to be run directly.
if __name__ == "__main__":
    create_tables()
    session = Session()
    try:
        load_metadata("data/smartviz_hierarchy.csv", session)
        load_usage("data/smartviz_occupancy_new_data.csv", session)
        print("Database initialized and data loaded.")
    except Exception as e:
        print(f"Error during DB setup: {e}")
    finally:
        session.close()
