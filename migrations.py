from sqlalchemy.orm import sessionmaker
from models import Base, engine

def run_migrations():
    Base.metadata.create_all(engine)
    print("Migrasi selesai! Tabel berhasil dibuat.")

def drop_tables():
    Base.metadata.drop_all(engine)
    print("Tabel berhasil dihapus.")

if __name__ == "__main__":
    drop_tables()
    run_migrations()