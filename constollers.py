from sqlalchemy.orm import sessionmaker
from models import AISHistory, engine, NMEA
import datetime

# Buat session factory
Session = sessionmaker(bind=engine)

def save_ais_data(mmsi, lat, lon, sog, cog, ship_type):
    """
    Menyimpan data AIS ke database.
    """
    with Session() as session:
        try:
            ais_data = AISHistory(mmsi=mmsi, lat=lat, lon=lon, sog=sog, cog=cog, ship_type=ship_type)
            session.add(ais_data)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e

def get_latest_ship_positions():
    """
    Mengambil 20 posisi kapal terbaru dari database.
    """
    with Session() as session:
        ships = session.query(AISHistory).order_by(AISHistory.received_at.desc()).limit(20).all()
        return [(ship.mmsi, ship.lat, ship.lon, ship.sog, ship.cog) for ship in ships]

def delete_old_records():
    """
    Menghapus record AIS yang lebih lama dari 23 minggu.
    """
    with Session() as session:
        try:
            cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(weeks=23)
            session.query(AISHistory).filter(AISHistory.received_at < cutoff_date).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            raise e

def get_all_ais_data():
    """
    Mengambil semua data AIS terbaru (20 record terakhir).
    """
    with Session() as session:
        ais_data = session.query(AISHistory).order_by(AISHistory.received_at.desc()).limit(20).all()
        return [{
            "id": ship.id,
            "mmsi": ship.mmsi,
            "lat": ship.lat,
            "lon": ship.lon,
            "sog": ship.sog,
            "cog": ship.cog,
            "ship_type": ship.ship_type,
            "received_at": ship.received_at.isoformat() if ship.received_at else None
        } for ship in ais_data]

def get_ais_latest():
    """
    Mengambil 10 data NMEA terbaru.
    """
    with Session() as session:
        query = session.query(NMEA.nmea).order_by(NMEA.created_at.desc()).limit(10)
        result = session.execute(query).fetchall()
        return [row[0] for row in result]

def save_nmea_data(nmea_data):
    """
    Menyimpan data NMEA ke database.
    """
    with Session() as session:
        try:
            timestamp = datetime.datetime.now()
            timestamp_str = timestamp.isoformat()
            nmea = NMEA(nmea=nmea_data, created_at=timestamp, updated_at=timestamp)
            session.add(nmea)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e