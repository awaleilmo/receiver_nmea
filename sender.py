import sqlite3
import socket
import time
from config import DB_NAME, UDP_IP, UDP_PORT, ALLOWED_MMSI, HOST, PORT
from constollers import get_ais_latest


def extract_mmsi(nmea_sentence):
    """Ekstrak MMSI dari pesan AIS (format AIVDM)"""
    try:
        parts = nmea_sentence.split(",")
        if parts[0].start:
            payload = parts[5]  # Payload AIS ada di bagian ke-6 (index 5)
            return payload[:9]  # MMSI biasanya 9 digit pertama dari payload
    except:
        pass
    return None


def send_ais_data():
    """Mengirim data AIS ke OpenCPN secara real-time."""
    global running_sender
    running_sender = True

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        while running_sender:
            ais_data = get_ais_latest()
            for nmea_sentence in ais_data:
                mmsi = extract_mmsi(nmea_sentence)
                if not ALLOWED_MMSI or (mmsi and mmsi in ALLOWED_MMSI):
                    udp_socket.sendto(nmea_sentence.encode("utf-8"), (UDP_IP, UDP_PORT))
                    print(f"Mengirim ke OpenCPN: {nmea_sentence}")
            time.sleep(2)  # Tunggu sebelum mengirim ulang


def stop_ais_sender():
    global running_sender
    running_sender = False

