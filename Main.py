import sys
import os
import sqlite3
import migrations
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from Pages.Main_page import AISViewer
from Untils.path_helper import get_resource_path


def Checkmigrate():
    try:
        db_path = get_resource_path("nmea_data.db", is_database=True)
        # Cek apakah file database ada
        if not os.path.exists(db_path):
            return True

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('config', 'connection', 'sender')")
        tables = cursor.fetchall()

        if len(tables) >= 3:
            cursor.execute("SELECT COUNT(*) FROM config")
            config_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM sender")
            sender_count = cursor.fetchone()[0]

            if config_count > 0 and sender_count > 0:
                return False

        conn.close()
        return True
    except Exception as e:
        print(f"Error saat memeriksa database: {e}")
        return True


def MigrateRun():
    try:


        print("Menjalankan migrasi standar...")
        migrations.run_migrations()

        print("Menjalankan seeder data...")
        migrations.run_seeder()

        print("Setup database selesai!")
        return True
    except Exception as e:
        print(f"Error saat migrasi: {e}")
        return False


if __name__ == "__main__":
    # Cek migrate
    if Checkmigrate():
        print("Database belum setup, menjalankan migrasi...")
        MigrateRun()

    app = QApplication(sys.argv)
    QApplication.setOrganizationName("Integra Corp")
    QApplication.setApplicationName("NMEA Receiver IPM")
    QApplication.setApplicationDisplayName("NMEA Receiver IPM")
    QApplication.setWindowIcon(QIcon(get_resource_path("Assets/logo_ipm.png")))
    window = AISViewer()
    window.show()
    sys.exit(app.exec())