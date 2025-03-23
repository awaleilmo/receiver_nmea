from sqlalchemy.orm import sessionmaker

from Models import nmea_data
from Models.__init__ import engine
import datetime

# Buat session factory
Session = sessionmaker(bind=engine)

def save_nmea_data(data, connection_ids):
    connection_id = connection_ids
    nmea = data

    with Session() as session:
        timestamp = datetime.datetime.utcnow()
        try:
            nmea_data_res = nmea_data(nmea=nmea, connection_id=connection_id, upload=False, created_at=timestamp, updated_at=timestamp)
            session.add(nmea_data_res)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e

def get_pending_data(batas=350):
    """Mengambil maksimal 350 data yang belum terkirim ke API."""
    with Session() as session:
        query = session.query(nmea_data).filter_by(upload=False).order_by(nmea_data.created_at).limit(batas).all()
        session.close()
        return query

def mark_data_as_sent(ids):
    """Menandai data sebagai terkirim (upload = True)."""
    with Session() as session:
        session.query(nmea_data).filter(nmea_data.id.in_(ids)).update({"upload": True}, synchronize_session=False)
        session.commit()
        session.close()

def get_ais_latest():
    """Mengambil 2 data NMEA terbaru."""
    with Session() as session:
        query = session.query(nmea_data.nmea).order_by(nmea_data.received_at.desc()).limit(2)
        result = session.execute(query).fetchall()
        return [row[0] for row in result]
