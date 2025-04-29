from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class SenderModel(Base):
    __tablename__ = "sender"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    host = Column(String, nullable=True)
    port = Column(String, nullable=True)
    network = Column(String, nullable=True)
    last_send_id = Column(Integer, nullable=True, default=0)
    active = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow())
    updated_at = Column(DateTime, default=datetime.datetime.utcnow())