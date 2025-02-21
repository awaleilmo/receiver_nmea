import sqlite3
import socket
from config import DB_NAME, OPENCPN_HOST, OPENCPN_PORT, ALLOWED_MMSI


def get_nmea_data():
    """Mengambil data terbaru dari database"""
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    cursor.execute("SELECT nmea FROM nmea ORDER BY id DESC LIMIT 10")  # Ambil 10 data terbaru
    rows = cursor.fetchall()
    connection.close()
    return [row[0] for row in rows]


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


def send_to_opencpn():
    """Mengirim data AIS yang sesuai filter ke OpenCPN"""
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    for nmea_sentence in get_nmea_data():
        mmsi = extract_mmsi(nmea_sentence)
        if not ALLOWED_MMSI or (mmsi and mmsi in ALLOWED_MMSI):
            udp_socket.sendto(nmea_sentence.encode("utf-8"), (OPENCPN_HOST, OPENCPN_PORT))
            print(f"Mengirim ke OpenCPN: {nmea_sentence}")

    udp_socket.close()


if __name__ == "__main__":
    send_to_opencpn()
