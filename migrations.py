import time

from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker, close_all_sessions
from Models import Base, engine, ConfigModel, ConnectionModel, SenderModel
import os
import configparser
from Untils.path_helper import get_resource_path

def reset_database_connection():
    print("\n Mereset koneksi database...")
    close_all_sessions()
    engine.dispose()
    if 'sqlite' in engine.url.drivername and engine.url.database != ':memory:':
        engine.connect()

def verify_tables_created(expected_tables):
    """Verifikasi tabel yang dibuat dengan retry mechanism"""
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        missing_tables = set(expected_tables) - existing_tables

        if not missing_tables:
            return True

        print(f"⏳ Menunggu tabel dibuat (Attempt {attempt}/{max_retries})...")
        time.sleep(1 * attempt)  # Exponential backoff

    print(f"❌ Tabel yang tidak terbentuk: {missing_tables}")
    return False

def verify_database_connection():
    """Verifikasi koneksi database dan lokasi file"""
    print("\n🔍 Verifikasi Database:")
    print(f"Database URL: {engine.url}")

    if 'sqlite' in engine.url.drivername:
        db_path = engine.url.database
        if db_path != ':memory:':
            print(f"Lokasi file SQLite: {os.path.abspath(db_path)}")
            print(f"File ada: {os.path.exists(db_path)}")
            print(f"Ukuran file: {os.path.getsize(db_path) if os.path.exists(db_path) else 0} bytes")

    try:
        with engine.connect() as conn:
            print("✅ Koneksi database berhasil")
    except Exception as e:
        print(f"❌ Gagal terhubung ke database: {str(e)}")
        return False
    return True

def show_tables(detailed=False):
    """Menampilkan tabel dengan lebih detail"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print("\n📊 TABEL SAAT INI:")
    if not tables:
        print("(Tidak ada tabel)")
        return

    for table in tables:
        columns = inspector.get_columns(table)
        print(f"┌─ {table}")
        for col in columns:
            print(f"├── {col['name']}: {col['type']}")
        print("└─" + "─" * 50)

def run_migrations():
    """Opsi 1: Migrasi standar"""
    print("\n🛠️ Menjalankan migrasi standar...")

    if not verify_database_connection():
        return

    reset_database_connection()
    time.sleep(0.5)

    expected_tables = list(Base.metadata.tables.keys())
    print(f"\n🛠️ Membuat tabel: {expected_tables}")

    try:
        Base.metadata.create_all(engine)

        if not verify_tables_created(expected_tables):
            raise RuntimeError("Gagal memverifikasi tabel dibuat")

        print("\n✅ Migrasi berhasil!")
        show_tables()

    except Exception as e:
        print(f"\n❌ Gagal migrasi: {str(e)}")
        # Force cleanup jika gagal
        engine.dispose()
        if 'sqlite' in engine.url.drivername and engine.url.database != ':memory:':
            db_path = engine.url.database
            if os.path.exists(db_path):
                print(f"⚠️ Mencoba menghapus file database: {db_path}")
                os.remove(db_path)

def refresh_migrations():
    """Opsi 2: Migrasi ulang"""
    print("\n💥 Memulai migrasi ulang (full refresh)...")

    if not verify_database_connection():
        return

    reset_database_connection()

    with engine.begin() as conn:
        Base.metadata.drop_all(conn)
        print("🗑️ Semua tabel dihapus")

    reset_database_connection()
    time.sleep(1)

    expected_tables = list(Base.metadata.tables.keys())
    print(f"\n🛠️ Membangun ulang tabel: {expected_tables}")

    try:
        Base.metadata.create_all(engine)

        if not verify_tables_created(expected_tables):
            raise RuntimeError("Tabel tidak terbentuk setelah migrasi")

        print("\n✅ Migrasi ulang berhasil!")
        show_tables()

    except Exception as e:
        print(f"\n❌ Gagal migrasi ulang: {str(e)}")
        if 'sqlite' in engine.url.drivername:
            print("💡 Tips: Coba hapus manual file database jika masalah berlanjut")

def run_seeder():
    """Seeder data utama"""
    print("\n🌱 Menjalankan seeder data...")

    Session = sessionmaker(bind=engine)
    session = Session()
    config_path = get_resource_path("config.ini", is_config=True)
    config = configparser.ConfigParser()
    config.read(config_path)

    try:
        # Data Config
        config_data = [
            ConfigModel(api_server=config['API']['AIS']),
            # Tambahkan data config lain jika diperlukan
        ]

        # Data Connection
        connection_data = [
            ConnectionModel(
                name="Test UDP",
                type="network",
                protocol="nmea0183",
                network="udp",
                address="127.0.0.1",
                port="10110",
                active=1
            ),
        ]

        sender = [
            SenderModel(
                name="Sender OpenCpn",
                host="localhost",
                port="10110",
                network="udp",
                last_send_id=0,
                active=1
            )
        ]

        # Hapus data existing (jika ada)
        print("🧹 Membersihkan data lama...")
        session.query(ConfigModel).delete()
        session.query(ConnectionModel).delete()

        # Tambahkan data baru
        print("🪴 Menanam data baru...")
        session.add_all(config_data + connection_data + sender)
        session.commit()

        # Verifikasi
        print("\n📊 Hasil Seeding:")
        print(f"Config: {session.query(ConfigModel).count()} data")
        print(f"Connection: {session.query(ConnectionModel).count()} data")
        print(f"Sender: {session.query(SenderModel).count()} data")

        print("\n🔍 Sample Data:")
        print("👤 Config:", session.query(ConfigModel).first().__dict__)
        print("👤 Connection:", session.query(ConnectionModel).first().__dict__)
        print("👤 Sender:", session.query(SenderModel).first().__dict__)

        print("\n✅ Seeder berhasil dijalankan")

    except Exception as e:
        session.rollback()
        print(f"❌ Gagal seeding: {str(e)}")
    finally:
        session.close()

def show_menu():
    """Menampilkan menu utama"""
    print("\n" + "="*50)
    print("SUPER DATABASE MANAGER".center(50))
    print("="*50)

    print("\nPilihan:")
    print("1. Migrasi Standar (tambah tabel/kolom baru)")
    print("2. Migrasi Ulang (hapus semua & buat baru)")
    print("3. Jalankan Seeder")
    print("4. Keluar")

    try:
        choice = input("Pilihan [1-4]: ").strip()
        return choice
    except Exception:
        return "0"

if __name__ == "__main__":
    while True:
        choice = show_menu()

        if choice == "1":
            run_migrations()
        elif choice == "2":
            refresh_migrations()
        elif choice == "3":
            run_seeder()
        elif choice == "4":
            print("Keluar dari aplikasi...")
            break
        else:
            print("Pilihan tidak valid!")