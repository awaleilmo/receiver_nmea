import sqlite3
import datetime
import socket

# Konfigurasi koneksi NMEA
HOST = "127.0.0.1"  # Ganti dengan alamat IP sumber data NMEA
PORT = 10110  # Ganti dengan port sumber data NMEA


# Fungsi untuk membuat tabel jika belum ada
def create_table():
    connection = sqlite3.connect("nmea_data.db")
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nmea (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nmea TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    connection.commit()
    connection.close()


# Fungsi untuk menyimpan data NMEA ke dalam database
def save_to_database(nmea_data):
    connection = sqlite3.connect("nmea_data.db")
    cursor = connection.cursor()
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO nmea (nmea, created_at, updated_at)
        VALUES (?, ?, ?)
    """, (nmea_data, timestamp, timestamp))
    connection.commit()
    connection.close()


# Fungsi untuk menerima data NMEA dari socket
def receive_nmea_tcp():
    # Membuka koneksi socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"Terhubung ke {HOST}:{PORT}, menunggu data NMEA...")

        while True:
            try:
                # Menerima data
                data = s.recv(1024).decode("utf-8")
                if not data:
                    break

                # Memproses setiap baris NMEA (data biasanya dipisahkan oleh newline)
                nmea_lines = data.strip().split("\n")
                for line in nmea_lines:
                    print(f"Menerima: {line}")
                    save_to_database(line)
            except Exception as e:
                print(f"Terjadi kesalahan: {e}")
                break

def receive_nmea_udp():
    # Membuka socket UDP
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((HOST, PORT))
        print(f"Menunggu data NMEA di {HOST}:{PORT}...\nTekan Ctrl+C untuk menghentikan.")

        while True:
            try:
                # Terima data dari pengirim
                data, addr = sock.recvfrom(1024)  # Maksimal 1024 byte
                nmea_data = data.decode("utf-8").strip()
                print(f"Diterima dari {addr}: {nmea_data}")

                # Simpan data ke database
                save_to_database(nmea_data)
            except Exception as e:
                print(f"Terjadi kesalahan: {e}")
                break

if __name__ == "__main__":
    # Membuat tabel jika belum ada
    create_table()

    # Memulai penerimaan data NMEA
    try:
        receive_nmea_udp()
    except KeyboardInterrupt:
        print("Program dihentikan.")
