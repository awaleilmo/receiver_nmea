import sqlite3
import datetime
from config import DB_NAME

def create_table():
    """Membuat tabel database jika belum ada."""
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    # Tabel utama NMEA
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nmea (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nmea TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Tabel history pergerakan kapal
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ais_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mmsi TEXT NOT NULL,
            lat REAL,
            lon REAL,
            sog REAL,  -- Speed Over Ground (Kecepatan)
            cog REAL,  -- Course Over Ground (Arah Kapal)
            ship_type TEXT,
            received_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()

def save_to_database(nmea_data):
    """Menyimpan data NMEA ke database SQLite."""
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute("INSERT INTO nmea (nmea, created_at, updated_at) VALUES (?, ?, ?)", (nmea_data, timestamp, timestamp))
    connection.commit()
    connection.close()

def save_ais_data(mmsi, lat, lon, sog, cog, ship_type):
    """Menyimpan data AIS yang sudah didecode ke database."""
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    timestamp = datetime.datetime.now().isoformat()

    cursor.execute("""
            INSERT INTO ais_history (mmsi, lat, lon, sog, cog, ship_type, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (mmsi, lat, lon, sog, cog, ship_type, timestamp))

    connection.commit()
    connection.close()
