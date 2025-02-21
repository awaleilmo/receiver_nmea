import os
import sqlite3
from config import DB_NAME
from database import create_table


def reset_database():
    """Menghapus database lama dan membuat ulang tabel-tabel"""
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"Database {DB_NAME} dihapus.")

    create_table()
    print("Database berhasil dibuat ulang.")


if __name__ == "__main__":
    reset_database()
