import os
import sqlite3
from config import DB_NAME


def reset_database():
    """Menghapus database lama dan membuat ulang tabel-tabel"""
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"Database {DB_NAME} dihapus.")

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    # Tabel utama untuk data AIS/NMEA
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nmea (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nmea TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Tabel untuk menyimpan history pergerakan kapal
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ais_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mmsi TEXT NOT NULL,
            nmea TEXT NOT NULL,
            received_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()
    print("Database berhasil dibuat ulang.")


if __name__ == "__main__":
    reset_database()
