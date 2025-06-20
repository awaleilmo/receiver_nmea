from sqlalchemy import Column, Integer, String, Float, DateTime, SMALLINT, Boolean
from sqlalchemy.dialects.mssql import TINYINT
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class nmea_data(Base):
    __tablename__ = "nmea_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    connection_id = Column(Integer, nullable=True)
    nmea = Column(String, nullable=True)
    upload = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc),
                        onupdate=lambda: datetime.datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc))