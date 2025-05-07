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
        timestamp = datetime.datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc)
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

def get_ais_latest(last_send_id=None):
    with Session() as session:
        query = session.query(nmea_data.id, nmea_data.nmea)
        if last_send_id:
            query = query.filter(nmea_data.id > last_send_id)
        else:
            utc_now = datetime.datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc)
            ten_seconds_ago = utc_now - datetime.timedelta(seconds=10)
            query = query.filter(nmea_data.created_at >= ten_seconds_ago)

        query = query.order_by(nmea_data.id.asc()).limit(1000)

        results = session.execute(query).fetchall()
        return results