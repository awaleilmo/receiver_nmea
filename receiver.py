import socket
from database import save_to_database
from config import HOST, PORT

def extract_mmsi(nmea_sentence):
    """Ekstrak MMSI dari pesan AIS (format AIVDM)"""
    try:
        parts = nmea_sentence.split(",")
        if parts[0].startswith("!AIVDM"):
            payload = parts[5]  # Payload AIS ada di bagian ke-6 (index 5)
            return payload[:9]  # MMSI biasanya 9 digit pertama dari payload
    except:
        pass
    return None

def receive_nmea_tcp():
    """Menerima data NMEA dari koneksi TCP."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"Terhubung ke {HOST}:{PORT}, menunggu data NMEA...")

        while True:
            try:
                data = s.recv(1024).decode("utf-8")
                if not data:
                    break

                nmea_lines = data.strip().split("\n")
                for line in nmea_lines:
                    print(f"Menerima: {line}")
                    save_to_database(line)
            except Exception as e:
                print(f"Terjadi kesalahan: {e}")
                break

def receive_nmea_udp():
    """Menerima data NMEA dari koneksi UDP."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((HOST, PORT))
        print(f"Menunggu data NMEA di {HOST}:{PORT}...\nTekan Ctrl+C untuk menghentikan.")

        while True:
            try:
                data, addr = sock.recvfrom(1024)
                nmea_data = data.decode("utf-8").strip()
                print(f"Diterima dari {addr}: {nmea_data}")

                save_to_database(nmea_data)

                # Simpan history berdasarkan MMSI
                mmsi = extract_mmsi(nmea_data)
                if mmsi:
                    save_ais_history(mmsi, nmea_data)
            except Exception as e:
                print(f"Terjadi kesalahan: {e}")
                break

if __name__ == "__main__":
    receive_nmea_udp()