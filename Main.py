import sys
import os
import sqlite3
import migrations
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from Pages.Main_page import AISViewer
from Untils.path_helper import get_resource_path

def get_app_dir():
    """Mendapatkan direktori tempat aplikasi dijalankan"""
    if getattr(sys, 'frozen', False):
        # Jika dijalankan sebagai executable (PyInstaller)
        return os.path.dirname(sys.executable)
    else:
        # Jika dijalankan sebagai script Python
        return os.path.dirname(os.path.abspath(__file__))

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


def initialize_config():
    """Membuat config.ini di folder yang sama dengan executable"""
    app_dir = get_app_dir()
    config_path = os.path.join(app_dir, "config.ini")

    print(f"🛠 Mencoba membuat config.ini di: {config_path}")  # Debug

    # Pastikan folder ada
    try:
        os.makedirs(app_dir, exist_ok=True)
    except Exception as e:
        print(f"⚠️ Gagal membuat folder: {e}")

    if not os.path.exists(config_path):
        print("🛠 Membuat config.ini baru...")
        default_config = """[API]
AIS = http://localhost:3002/api/v1/ais/bulk
GET_STATION = http://localhost:3002/api/v1/station/check
POST_STATION = http://localhost:3002/api/v1/station
"""
        try:
            with open(config_path, 'w') as f:
                f.write(default_config)
            print(f"✅ Berhasil membuat config.ini di: {config_path}")

            # Verifikasi file benar-benar ada
            if os.path.exists(config_path):
                print("🔍 Verifikasi: File config.ini berhasil dibuat")
            else:
                print("❌ Verifikasi: File config.ini tidak terdeteksi setelah pembuatan")

        except Exception as e:
            print(f"❌ Gagal membuat config.ini: {e}")
            print(f"Detail error: {str(e)}")

            # Coba alternatif lokasi jika gagal
            alt_path = os.path.join(os.path.expanduser("~"), "nmea_config.ini")
            print(f"⚠️ Mencoba alternatif path: {alt_path}")
            try:
                with open(alt_path, 'w') as f:
                    f.write(default_config)
                print(f"✅ Berhasil membuat config alternatif di: {alt_path}")
                return alt_path
            except Exception as alt_e:
                print(f"❌ Gagal membuat config alternatif: {alt_e}")
                raise
    else:
        print(f"✅ Config.ini sudah ada di: {config_path}")

    return config_path

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
    # Inisialisasi config (hanya dibuat jika belum ada)
    config_file = initialize_config()
    print(f"✅ Config file: {config_file}")

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