from sqlalchemy import Column, Integer, String, Float, DateTime, SMALLINT, Boolean
from sqlalchemy.dialects.mssql import TINYINT
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class ais_satic(Base):
    __tablename__ = "ais_static"

    id = Column(Integer, primary_key=True)
    mmsi = Column(String, nullable=True)
    ais_version = Column(Integer, nullable=True)
    imo_number = Column(String, nullable=True)
    callsign = Column(String, nullable=True)
    shipname = Column(String, nullable=True)
    shiptype = Column(String, nullable=True)
    dimension_to_bow = Column(SMALLINT, nullable=True)
    dimension_to_stern = Column(SMALLINT, nullable=True)
    dimension_to_port = Column(SMALLINT, nullable=True)
    dimension_to_starboard = Column(SMALLINT, nullable=True)
    position_fix_type = Column(Integer, nullable=True)
    eta = Column(DateTime, nullable=True)
    draught = Column(Float, nullable=True)
    destination = Column(String, nullable=True)
    dte = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow())
    updated_at = Column(DateTime, default=datetime.datetime.utcnow())

class ais_data(Base):
    __tablename__ = "ais_data"

    id = Column(Integer, primary_key=True)
    connection_id = Column(Integer, nullable=True)
    mmsi = Column(String, nullable=True)
    nav_status = Column(Integer, nullable=True)
    rot = Column(Float, nullable=True)
    sog = Column(Float, nullable=True)
    position_accuracy = Column(Integer, nullable=True)
    longitude = Column(Float, nullable=True)
    latitude = Column(Float, nullable=True)
    cog = Column(Float, nullable=True)
    true_heading = Column(Integer, nullable=True)
    timestamp_utc = Column(DateTime, nullable=True)
    special_manoeuver = Column(Integer, nullable=True)
    raim = Column(Integer, nullable=True)
    sync_state = Column(Integer, nullable=True)
    slot_timeout = Column(Integer, nullable=True)
    slot_offset = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow())
    updated_at = Column(DateTime, default=datetime.datetime.utcnow())

class nmea_data(Base):
    __tablename__ = "nmea_data"

    id = Column(Integer, primary_key=True)
    connection_id = Column(Integer, nullable=True)
    nmea = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow())
    updated_at = Column(DateTime, default=datetime.datetime.utcnow())