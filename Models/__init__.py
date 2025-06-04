import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

from Models.NMEA_model import nmea_data
from Models.Config_model import ConfigModel
from Models.Connection_model import ConnectionModel
from Models.Sender_model import SenderModel
from Untils.path_helper import get_resource_path

Base = declarative_base()
db_path = get_resource_path("nmea_data.db", is_database=True)
engine = create_engine(f"sqlite:///{db_path}")

nmea_data.__table__.create(bind=engine, checkfirst=True)
ConfigModel.__table__.create(bind=engine, checkfirst=True)
ConnectionModel.__table__.create(bind=engine, checkfirst=True)
SenderModel.__table__.create(bind=engine, checkfirst=True)
