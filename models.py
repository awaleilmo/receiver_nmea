import datetime
from config import DB_NAME
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
engine = create_engine(f"sqlite:///{DB_NAME}")

class AISHistory(Base):
    __tablename__ = "ais_history"

    id = Column(Integer, primary_key=True)
    mmsi = Column(String, nullable=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    sog = Column(Float, nullable=True)
    cog = Column(Float, nullable=True)
    ship_type = Column(String, nullable=True)
    received_at = Column(DateTime, default=datetime.datetime.utcnow())

class NMEA(Base):
    __tablename__ = "nmea"

    id = Column(Integer, primary_key=True)
    nmea = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow())
    updated_at = Column(DateTime, default=datetime.datetime.utcnow())