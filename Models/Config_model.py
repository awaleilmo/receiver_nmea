from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class ConfigModel(Base):
    __tablename__ = "config"

    id = Column(Integer, primary_key=True)
    cpn_host = Column(String, nullable=True)
    cpn_port = Column(String, nullable=True)
    api_server = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow())
    updated_at = Column(DateTime, default=datetime.datetime.utcnow())