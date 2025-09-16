# Defines the database table structures (ORM models) for SQLAlchemy so python code can interact with DB tables.
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey # Import SQLAlchemy column types and foreign key support.
from sqlalchemy.ext.declarative import declarative_base # provide Base class to define table models.
from sqlalchemy.orm import relationship # allows linking tables (for easy joins).
import datetime # for setting default timestamps

Base = declarative_base() # all models/tables inherit from this, and it tells SQLAlchemy they are DB models/tables.

# ---- User Table ----
# This maps to user table.
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True) #unique user id
    username = Column(String(50), unique=True, nullable=False) # unique username
    hashed_password = Column(String(128), nullable=False) #for storing password securely.
    created_at = Column(DateTime, default=datetime.datetime.utcnow) #auto timestamp

# ---- Chat History Table ----
# Tracks user queries and system responses.
class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True) 
    user_id = Column(Integer) #who made the query
    query = Column(String) # User's question.
    response = Column(String) # ssystems reply.
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# ---- Metadata Table ----
# Info about rooms, floors, areas.
class SpaceMetadata(Base):
    __tablename__ = "space_metadata"

    id = Column(Integer, primary_key=True)
    Area = Column(String)
    Floor = Column(Integer)
    Room_Name = Column(String)
    geometry_id = Column(String, unique=True, nullable=False) # unique identifier for spatial join.
    parent_id = Column(Integer)

    # Link to space_usage
    usage_records = relationship("SpaceUsage", back_populates="space", cascade="all, delete")
    # back_populates -> allows bidirectional access and cascade -> delete usage records if usagespace deleted.

# ---- Time Series Occupancy Table ----
class SpaceUsage(Base):
    __tablename__ = "space_usage"

    id = Column(Integer, primary_key=True)
    frequency = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    metric_name = Column(String)
    aggregation = Column(String)
    value = Column(Float)

    geometry_id = Column(String, ForeignKey("space_metadata.geometry_id"))
    is_holiday = Column(Boolean)
    is_valid = Column(Boolean)
    is_working = Column(Boolean)
    hour = Column(Integer)
    dayofweek = Column(Integer)
    month = Column(Integer)

    # Link back to metadata
    space = relationship("SpaceMetadata", back_populates="usage_records")

