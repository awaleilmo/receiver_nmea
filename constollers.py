from sqlalchemy.orm import sessionmaker
from models import AISHistory, engine

Session = sessionmaker(bind=engine)
session = Session()


def save_ais_data(mmsi, lat, lon, sog, cog, ship_type):
    ais_data = AISHistory(mmsi=mmsi, lat=lat, lon=lon, sog=sog, cog=cog, ship_type=ship_type)
    session.add(ais_data)
    session.commit()

def get_latest_ship_positions():
    ships = session.query(AISHistory).order_by(AISHistory.received_at.desc()).limit(20).all()
    return [(ship.mmsi, ship.lat, ship.lon, ship.sog, ship.cog) for ship in ships]

def delete_old_records():
    session.query(AISHistory).filter(AISHistory.received_at < datetime.datetime.utcnow() - datetime.timedelta(weeks=23)).delete()
    session.commit()
