from sqlalchemy.orm import sessionmaker
from sqlalchemy import func

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
        return

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
        return

    with Session() as session:
        try:
            current_time = datetime.datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc)

            # Update dengan tracking yang lebih detail
            updated_count = session.query(nmea_data).filter(nmea_data.id.in_(ids)).update({
                "decode_status": "failed",
                "upload_error": reason,
                "last_upload_attempt": current_time,
                "upload_attempts": nmea_data.upload_attempts + 1
            }, synchronize_session=False)

            session.commit()
            signalsLogger.new_data_received.emit(f"Marked {updated_count} records as failed ({reason})")
            return updated_count
        except Exception as e:
            session.rollback()
            signalsLogger.new_data_received.emit(f"Error marking failed data: {str(e)}")
            raise e

def mark_data_as_decoded(ids):
    """
    Tandai data yang berhasil di-decode
    """
    if not ids:
        return

    with Session() as session:
        try:
            current_time = datetime.datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc)

            updated_count = session.query(nmea_data).filter(nmea_data.id.in_(ids)).update({
                "decode_status": "success",
                "last_upload_attempt": current_time,
                "upload_attempts": nmea_data.upload_attempts + 1
            }, synchronize_session=False)

            session.commit()
            return updated_count
        except Exception as e:
            session.rollback()
            raise e

def get_retry_candidates(limit=100):
    """
    Ambil kandidat untuk retry (failed records dengan attempts < 3)
    """
    with Session() as session:
        try:
            current_time = datetime.datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc)
            retry_time = current_time - datetime.timedelta(minutes=30)  # Retry after 30 minutes

            query = session.query(nmea_data).filter(
                nmea_data.decode_status == 'failed',
                nmea_data.upload_attempts < 3,
                (nmea_data.last_upload_attempt < retry_time) | (nmea_data.last_upload_attempt.is_(None))
            ).order_by(nmea_data.created_at).limit(limit).all()

            result = []
            for item in query:
                result.append({
                    'id': item.id,
                    'nmea': item.nmea,
                    'connection_id': item.connection_id,
                    'created_at': item.created_at,
                    'upload_attempts': item.upload_attempts,
                    'upload_error': item.upload_error
                })
            return result
        except Exception as e:
            session.rollback()
            raise e

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