from sqlalchemy.orm import sessionmaker

from Models import nmea_data
from Models.__init__ import engine
import datetime
from Services.SignalsMessages import signalsLogger

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

def batch_save_nmea(nmea_raw, connection_ids):
    lines = nmea_raw.strip().splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith("!AIVDM") or line.startswith("!AIVDO"):
            signalsLogger.new_data_received.emit(f"Diterima: {line}")
            save_nmea_data(line, connection_ids)

def get_pending_data(batas=350):
    with Session() as session:
        query = session.query(nmea_data).filter_by(upload=False).order_by(nmea_data.created_at).limit(batas).all()
        session.close()
        return query

def mark_data_as_sent(ids):
    with Session() as session:
        session.query(nmea_data).filter(nmea_data.id.in_(ids)).update({"upload": True}, synchronize_session=False)
        session.commit()
        session.close()

def get_ais_latest():
    with Session() as session:
        query = session.query(nmea_data.nmea).order_by(nmea_data.created_at.desc()).limit(2)
        result = session.execute(query).fetchall()
        return [row[0] for row in result]
