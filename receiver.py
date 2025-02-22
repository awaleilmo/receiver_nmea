import socket
import json
from pyais import decode
from database import save_to_database
from constollers import save_ais_data
from config import  HOST, PORT

ais_buffer = {}

def process_ais_message(nmea_sentence):
    """Mengelola pesan AIS multi-fragment sebelum didecode."""
    try:
        parts = nmea_sentence.split(",")

        if len(parts) < 7:
            return None, None, None, None, None, None  # Abaikan jika format tidak sesuai

        total_fragments = int(parts[1])  # Jumlah total fragmen
        fragment_number = int(parts[2])  # Nomor fragmen saat ini
        msg_id = parts[3]  # ID pesan (biasanya digunakan untuk menggabungkan fragmen)

        if total_fragments > 1:
            if msg_id not in ais_buffer:
                ais_buffer[msg_id] = [None] * total_fragments  # Buat buffer sesuai jumlah fragmen

            ais_buffer[msg_id][fragment_number - 1] = nmea_sentence  # Simpan fragmen

            # Jika semua fragmen sudah diterima, gabungkan dan decode
            if None not in ais_buffer[msg_id]:
                full_message = "".join(ais_buffer[msg_id])  # Gabungkan semua fragmen
                del ais_buffer[msg_id]  # Hapus buffer setelah selesai
                return extract_ais_data(full_message)
            else:
                return None, None, None, None, None, None  # Masih menunggu fragmen lain

        else:
            return extract_ais_data(nmea_sentence)  # Jika hanya satu fragmen, langsung decode

    except Exception as e:
        print(f"Error processing AIS message: {e}")
        return None, None, None, None, None, None

def extract_ais_data(nmea_sentence):
    """Decode data AIS menggunakan pyais."""
    try:
        decoded = decode(nmea_sentence)
        decoded_json = decoded.to_json()  # Konversi ke string JSON
        decoded_dict = json.loads(decoded_json)  # Parse ke dictionary

        mmsi = decoded_dict.get("mmsi")
        lat = decoded_dict.get("lat")
        lon = decoded_dict.get("lon")
        sog = decoded_dict.get("speed")  # Speed Over Ground
        cog = decoded_dict.get("course")  # Course Over Ground
        ship_type = decoded_dict.get("msg_type")  # Bisa diganti dengan tipe kapal lain jika tersedia

        return mmsi, lat, lon, sog, cog, ship_type
    except Exception as e:
        print(f"Error decoding AIS data: {e}")
    return None, None, None, None, None, None

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
    global running_receiver
    running_receiver = True

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((HOST, PORT))
        print(f"Menunggu data NMEA di {HOST}:{PORT}...\nTekan Ctrl+C untuk menghentikan.")

        while running_receiver:
            try:
                data, addr = sock.recvfrom(1024)
                nmea_data = data.decode("utf-8").strip()
                print(f"Diterima dari {addr}: {nmea_data}")

                save_to_database(nmea_data)

                # Simpan history berdasarkan MMSI
                mmsi, lat, lon, sog, cog, ship_type = process_ais_message(nmea_data)
                if mmsi:
                    save_ais_data(mmsi, lat, lon, sog, cog, ship_type)
            except Exception as e:
                print(f"Terjadi kesalahan: {e}")
                break

def stop_nmea_receiver():
    global running_receiver
    running_receiver = False

if __name__ == "__main__":
    receive_nmea_udp()