from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class ConnectionModel(Base):
    __tablename__ = "connection"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    type = Column(String, nullable=True)
    data_port = Column(String, nullable=True)
    baudrate = Column(String, nullable=True)
    protocol = Column(String, nullable=True)
    network = Column(String, nullable=True)
    address = Column(String, nullable=True)
    port = Column(String, nullable=True)
    active = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc),
                        onupdate=lambda: datetime.datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc))