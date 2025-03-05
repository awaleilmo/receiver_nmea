import datetime

from Models.AISHistory_model import AISHistory
from Models.Config_model import ConfigModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from Models.Connection_model import ConnectionModel

Base = declarative_base()
engine = create_engine(f"sqlite:///nmea_data.db")

AISHistory.__table__.create(bind=engine, checkfirst=True)
ConfigModel.__table__.create(bind=engine, checkfirst=True)
ConnectionModel.__table__.create(bind=engine, checkfirst=True)
