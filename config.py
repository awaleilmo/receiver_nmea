# Konfigurasi untuk penerima dan pengirim data AIS/NMEA

# Koneksi NMEA
HOST = "127.0.0.1"  # IP sumber data NMEA
PORT = 10110        # Port sumber data NMEA

# Database SQLite
DB_NAME = "nmea_data.db"

# Koneksi ke OpenCPN
UDP_IP = "127.0.0.1"
UDP_PORT = 10112

# Daftar MMSI kapal yang ingin dikirim (kosongkan [] jika ingin semua kapal)
ALLOWED_MMSI = []
