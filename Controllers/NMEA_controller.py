from sqlalchemy.orm import sessionmaker
from sqlalchemy import func, text

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
        try:
            query = session.query(nmea_data).filter_by(upload=False).order_by(nmea_data.created_at).limit(batas).all()

            result = []
            for item in query:
                result.append({
                    'id': item.id,
                    'nmea': item.nmea,
                    'connection_id': item.connection_id,
                    'created_at': item.created_at,
                    'upload': item.upload
                })
            return result
        except Exception as e:
            session.rollback()
            raise e

def get_pending_count():
    with Session() as session:
        try:
            count = session.query(func.count(nmea_data.id)).filter_by(upload=False).scalar()
            return count
        except Exception as e:
            session.rollback()
            raise e

def mark_data_as_sent(ids):
    if not ids:
        return 0

    with Session() as session:
        try:
            updated_count = session.query(nmea_data).filter(nmea_data.id.in_(ids)).update(
                {"upload": True}, synchronize_session=False
            )
            session.commit()
            signalsLogger.new_data_received.emit(f"Marked {updated_count} records as uploaded")
            return updated_count
        except Exception as e:
            session.rollback()
            signalsLogger.new_data_received.emit(f"Error marking data as sent: {str(e)}")
            raise e

def mark_data_as_failed(ids, reason="decode_failed"):
    """
    Tandai data yang gagal decode dengan tracking yang lebih baik
    """
    if not ids:
        return 0

    with Session() as session:
        try:
            # Update dengan tracking yang lebih detail
            updated_count = session.query(nmea_data).filter(nmea_data.id.in_(ids)).update({
                "upload": True,
            }, synchronize_session=False)

            session.commit()
            signalsLogger.new_data_received.emit(f"Marked {updated_count} records as failed ({reason})")
            return updated_count
        except Exception as e:
            session.rollback()
            signalsLogger.new_data_received.emit(f"Error marking failed data: {str(e)}")
            raise e

def get_decode_stats():

    with Session() as session:
        try:

            pending_count = session.query(func.count(nmea_data.id)).filter_by(upload=False).scalar()
            uploaded_count = session.query(func.count(nmea_data.id)).filter_by(upload=True).scalar()

            return {'pending': pending_count, 'uploaded': uploaded_count, 'total': pending_count + uploaded_count}
        except Exception as e:
            session.rollback()
            raise e

def get_recent_activity():

    with Session() as session:
        try:
            one_hour_ago = datetime.datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc) - datetime.timedelta(hours=1)

            recent_additions = session.query(func.count(nmea_data.id)).filter(nmea_data.created_at >= one_hour_ago).scalar()

            recent_uploads = session.query(func.count(nmea_data.id)).filter(nmea_data.upload == True, nmea_data.created_at >= one_hour_ago).scalar()

            return {'recent_additions': recent_additions, 'recent_uploads': recent_uploads}
        except Exception as e:
            session.rollback()
            raise e

def get_ais_latest(last_send_id=None):
    with Session() as session:
       try:
           query = session.query(nmea_data.id, nmea_data.nmea)
           if last_send_id:
               query = query.filter(nmea_data.id > last_send_id)
           else:
               utc_now = datetime.datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc)
               ten_seconds_ago = utc_now - datetime.timedelta(seconds=10)
               query = query.filter(nmea_data.created_at >= ten_seconds_ago)
           query = query.order_by(nmea_data.id.asc()).limit(1000)
           result = session.execute(query).fetchall()
           return result
       except Exception as e:
           session.rollback()
           raise e

def reset_failed_uploads():

    with Session() as session:
        try:
            old_timestamp = datetime.datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc) - datetime.timedelta(hours=2)

            reset_count = session.query(nmea_data).filter(
                nmea_data.upload == True,
                nmea_data.created_at < old_timestamp,
                nmea_data.created_at > old_timestamp
            ).update({"upload": False}, synchronize_session=False)
            session.commit()
            signalsLogger.new_data_received.emit(f"Reset {reset_count} potentially stuck records")
            return reset_count
        except Exception as e:
            session.rollback()
            raise e