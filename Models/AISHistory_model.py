from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class AISHistory(Base):
    __tablename__ = "ais_history"

    id = Column(Integer, primary_key=True)
    nmea = Column(String, nullable=False)
    mmsi = Column(String, nullable=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    sog = Column(Float, nullable=True)
    cog = Column(Float, nullable=True)
    ship_type = Column(String, nullable=True)
    received_at = Column(DateTime, default=datetime.datetime.utcnow())