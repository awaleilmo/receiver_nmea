import datetime
from config import DB_NAME
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
engine = create_engine(f"sqlite:///{DB_NAME}")

class AISHistory(Base):
    __tablename__ = "ais_history"

    id = Column(Integer, primary_key=True)
    mmsi = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    sog = Column(Float, nullable=False)
    cog = Column(Float, nullable=False)
    ship_type = Column(String, nullable=False)
    received_at = Column(DateTime, default=datetime.datetime.utcnow())
