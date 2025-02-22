from sqlalchemy.orm import sessionmaker
from models import Base, engine

def run_migrations():
    Base.metadata.create_all(engine)
    print("Migrasi selesai! Tabel berhasil dibuat.")

if __name__ == "__main__":
    run_migrations()