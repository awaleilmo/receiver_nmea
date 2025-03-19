import socket
import json
import time
import requests
import threading

import serial
import ais

from Controllers.AISHistory_controller import save_ais_data
from Controllers.Configure_controller import get_config
from Controllers.Connection_controller import get_connection

ais_buffer = {}

LARAVEL_API_URL = get_config()['api_server']

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

def test_ais_data(nmea_sentence):
    payload = nmea_sentence.split(",")[5]
    decoded_messages = ais.decode(payload, 0)

    # Cetak hasil dekode
    print(decoded_messages)

def extract_ais_data(nmea_sentence):
    """Decode data AIS menggunakan pyais."""
    try:
        from pyais import decode
        decoded = decode(nmea_sentence)
        decoded_json = decoded.to_json()  # Konversi ke string JSON
        decoded_dict = json.loads(decoded_json)  # Parse ke dictionary
        try:
            send_to_api = requests.post(LARAVEL_API_URL, json=decoded_dict)
            if send_to_api.status_code == 200 or send_to_api.status_code == 201:
                print(f"Berhasil mengirim data ke Laravel API: {send_to_api.text}")
            else:
                print(f"Gagal mengirim data ke Laravel API: {send_to_api.text}")
        except Exception as e:
            print('API is Off')

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

def receive_nmea_tcp(host, port, stop_event):
    while not stop_event.is_set():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Agar bisa di-restart tanpa error
                sock.bind((host, port))
                print(f"Menunggu data NMEA di {host}:{port}...\nTekan Ctrl+C untuk menghentikan.")

                while not stop_event.is_set():
                    sock.settimeout(1.0)
                    try:
                        data, addr = sock.accept()
                        nmea_data = data.decode("utf-8").strip()
                        print(f"Diterima dari {addr}: {nmea_data}")

                        # Simpan history berdasarkan MMSI
                        mmsi, lat, lon, sog, cog, ship_type = process_ais_message(nmea_data)
                        if mmsi:
                            save_ais_data(nmea_data, mmsi, lat, lon, sog, cog, ship_type)
                    except socket.timeout:
                        continue
        except Exception as e:
            print(f"Gagal bind ke {host}:{port}, mencoba lagi dalam 10 detik... Error: {e}")
            time.sleep(10)
        finally:
            print("Receiver stopped.")

def receive_nmea_udp(host, port, stop_event):
    """Menerima data NMEA dari koneksi UDP."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        sock.bind((host, port))
        print(f"Menunggu UDP data NMEA di {host}:{port}...\nTekan Ctrl+C untuk menghentikan.")

        count = 0
        start_time = time.time()

        while not stop_event.is_set():
            try:
                sock.settimeout(1.0)
                data, addr = sock.recvfrom(1024)
                count += 1

                if time.time() - start_time >= 60:
                    print(f"Total data diterima dalam 1 menit: {count}")
                    count = 0
                    start_time = time.time()

                nmea_data = data.decode("utf-8").strip()
                test_ais_data(nmea_data)
                # print(f"Diterima dari {port}: {nmea_data}")
                # mmsi, lat, lon, sog, cog, ship_type = process_ais_message(nmea_data)
                # if mmsi:
                #     save_ais_data(nmea_data, mmsi, lat, lon, sog, cog, ship_type)

            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error saat menerima data: {e}")

def receive_nmea_serial(port, baudrate, stop_event):
    """Menerima data NMEA AIS dari port serial (COM)."""
    ser = None  # Pastikan ser dideklarasikan sebelum try

    while not stop_event.is_set():
        try:
            ser = serial.Serial(port=port, baudrate=baudrate, timeout=0.5, exclusive=True)
            print(f"Menunggu data NMEA dari {port}...")

            while not stop_event.is_set():  # Perbaikan: Pakai ()
                if ser.in_waiting > 0:
                    nmea_data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore').strip()
                    print(f"Diterima dari {port}: {nmea_data}")
                    test_ais_data(nmea_data)

                        # Proses data AIS hanya jika valid
                        # mmsi, lat, lon, sog, cog, ship_type = process_ais_message(nmea_data)
                        # if mmsi:
                        #     save_ais_data(nmea_data, mmsi, lat, lon, sog, cog, ship_type)
                time.sleep(0.1)
        except serial.SerialException as e:  # Menangani error jika port tidak bisa dibuka
            print(f"Gagal bind ke {port} {baudrate}, mencoba lagi dalam 10 detik... Error: {e}")
            time.sleep(10)

        except Exception as e:  # Tangani error umum lainnya
            print(f"Error umum di receive_nmea_serial: {e}")

        finally:
            if ser is not None:  # Perbaikan: Cek apakah ser sudah dibuat sebelum ditutup
                try:
                    if ser.is_open:
                        ser.close()  # Tutup serial sebelum reconnect
                        print(f"Port {port} ditutup.")
                except Exception as e:
                    print(f"Error saat menutup serial {port}: {e}")

    print("Receiver serial stopped.")



def start_multi_receiver(stop_event):
    try:
        data = get_connection()
        threads = []
        has_active_connection = False

        for dataset in data:
                if dataset.get('active') == 0:
                    continue

                has_active_connection = True

                if dataset.get('type') == 'network':
                    thread = None  # Inisialisasi thread

                    protocol = dataset.get('network')
                    address = dataset.get('address')
                    port = dataset.get('port')

                    if not address or not port:
                        print(f"Konfigurasi tidak valid: {dataset}")
                        continue

                    if protocol == 'udp':
                        thread = threading.Thread(target=receive_nmea_udp, args=(address, int(port), stop_event))

                    elif protocol == 'tcp':
                        thread = threading.Thread(target=receive_nmea_tcp, args=(address, int(port), stop_event))

                    if thread:
                        thread.start()
                        threads.append(thread)
                        time.sleep(0.1)  # Hindari CPU overload
                elif dataset.get('type') == 'serial':

                    data_port = dataset.get('data_port')
                    baudrate = dataset.get('baudrate')

                    if not data_port or not baudrate:
                        print(f"Konfigurasi tidak valid: {dataset}")
                        continue

                    thread = threading.Thread(target=receive_nmea_serial, args=(data_port, int(baudrate), stop_event))
                    if thread:
                        thread.start()
                        threads.append(thread)
                        time.sleep(1)
                else:
                    print(f"Jenis dataset tidak valid: {dataset}")

        if not has_active_connection:
            print("⚠️ Tidak ada koneksi aktif! Menunggu stop_event...")
            while not stop_event.is_set():
                time.sleep(1)  # Biarkan berjalan agar bisa dihentikan
            print("Receiver dihentikan.")
        return threads

    except Exception as e:
        print(f"Error saat mengambil koneksi dari database: {e}")
        return []