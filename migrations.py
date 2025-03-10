from sqlalchemy.orm import sessionmaker
from Models import Base, engine, ConfigModel, ConnectionModel

def run_migrations():
    Base.metadata.create_all(engine)
    print("Migrasi selesai! Tabel berhasil dibuat.")

def drop_tables():
    Base.metadata.drop_all(engine)
    print("Tabel berhasil dihapus.")

def seeder_config():
    Session = sessionmaker(bind=engine)
    session = Session()
    seederConfig = ConfigModel(cpn_host="127.0.0.1", cpn_port="10112", api_server="http://localhost:8000/api/ais/store")
    session.add(seederConfig)
    session.commit()
    session.close()

def seeder_connection():
    Session = sessionmaker(bind=engine)
    session = Session()
    seederConnection = ConnectionModel(name="Test", type="network", data_port="", baudrate="", protocol="nmea0183", network="udp", address="127.0.0.1", port="10110", active=1)
    session.add(seederConnection)
    session.commit()
    session.close()

if __name__ == "__main__":
    drop_tables()
    run_migrations()
    seeder_config()
    seeder_connection()