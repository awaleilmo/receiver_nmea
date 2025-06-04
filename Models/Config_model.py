from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class ConfigModel(Base):
    __tablename__ = "config"

    id = Column(Integer, primary_key=True)
    api_server = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc),
                       onupdate=lambda: datetime.datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc))