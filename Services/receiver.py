import socket
import json
import time
import requests
import threading

import serial
import ais

from Controllers.NMEA_controller import save_nmea_data
from Controllers.Configure_controller import get_config
from Controllers.Connection_controller import get_connection

from Services.SignalsMessages import signals

ais_buffer = {}

LARAVEL_API_URL = get_config()['api_server']



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


def receive_nmea_tcp(host, port, stop_event, connection_id):
    while not stop_event.is_set():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Agar bisa di-restart tanpa error
                sock.bind((host, port))
                signals.new_data_received.emit(f"Menunggu data NMEA di {host}:{port}...\nTekan Ctrl+T untuk menghentikan.")
                count = 0
                start_time = time.time()

                while not stop_event.is_set():
                    sock.settimeout(1.0)
                    try:
                        data, addr = sock.accept()
                        nmea_data = data.decode("utf-8").strip()
                        signals.new_data_received.emit(f"Diterima dari {addr}: {nmea_data}")

                        if time.time() - start_time >= 60:
                            signals.new_data_received.emit(f"Total data diterima dalam 1 menit: {count}")
                            count = 0
                            start_time = time.time()

                        save_nmea_data(nmea_data, connection_id)

                    except socket.timeout:
                        continue
        except Exception as e:
            signals.new_data_received.emit(f"Gagal bind ke {host}:{port}, mencoba lagi dalam 10 detik... Error: {e}")
            time.sleep(10)
        finally:
            signals.new_data_received.emit("Receiver stopped.")


def receive_nmea_udp(host, port, stop_event, connection_id):
    """Menerima data NMEA dari koneksi UDP."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        sock.bind((host, port))
        signals.new_data_received.emit(f"Menunggu UDP data NMEA di {host}:{port}...\nTekan Ctrl+T untuk menghentikan.")

        count = 0
        start_time = time.time()

        while not stop_event.is_set():
            try:
                sock.settimeout(1.0)
                data, addr = sock.recvfrom(1024)
                count += 1

                if time.time() - start_time >= 60:
                    signals.new_data_received.emit(f"Total data diterima dalam 1 menit: {count}")
                    count = 0
                    start_time = time.time()

                nmea_data = data.decode("utf-8").strip()
                save_nmea_data(nmea_data, connection_id)

            except socket.timeout:
                continue
            except Exception as e:
                signals.new_data_received.emit(f"Error saat menerima data: {e}")


def receive_nmea_serial(port, baudrate, stop_event, connection_id):
    """Menerima data NMEA AIS dari port serial (COM)."""
    ser = None  # Pastikan ser dideklarasikan sebelum try

    while not stop_event.is_set():
        try:
            ser = serial.Serial(port=port, baudrate=baudrate, timeout=0.5, exclusive=True)
            signals.new_data_received.emit(f"Menunggu data NMEA dari {port}...")

            count = 0
            start_time = time.time()

            while not stop_event.is_set():  # Perbaikan: Pakai ()
                if ser.in_waiting > 0:

                    if time.time() - start_time >= 60:
                        signals.new_data_received.emit(f"Total data diterima dalam 1 menit: {count}")
                        count = 0
                        start_time = time.time()
                    nmea_data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore').strip()
                    signals.new_data_received.emit(f"Diterima dari {port}: {nmea_data}")
                    save_nmea_data(nmea_data, connection_id)

                time.sleep(0.05)
        except serial.SerialException as e:  # Menangani error jika port tidak bisa dibuka
            signals.new_data_received.emit(f"Gagal bind ke {port} {baudrate}, mencoba lagi dalam 10 detik... Error: {e}")
            time.sleep(10)

        except Exception as e:  # Tangani error umum lainnya
            signals.new_data_received.emit(f"Error umum di receive_nmea_serial: {e}")

        finally:
            if ser is not None:  # Perbaikan: Cek apakah ser sudah dibuat sebelum ditutup
                try:
                    if ser.is_open:
                        ser.close()  # Tutup serial sebelum reconnect
                        signals.new_data_received.emit(f"Port {port} ditutup.")
                except Exception as e:
                    signals.new_data_received.emit(f"Error saat menutup serial {port}: {e}")

    signals.new_data_received.emit("Receiver serial stopped.")


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
                    signals.new_data_received.emit(f"Konfigurasi tidak valid: {dataset}")
                    continue

                if protocol == 'udp':
                    thread = threading.Thread(target=receive_nmea_udp,
                                              args=(address, int(port), stop_event, dataset.get('id')))

                elif protocol == 'tcp':
                    thread = threading.Thread(target=receive_nmea_tcp,
                                              args=(address, int(port), stop_event, dataset.get('id')))

                if thread:
                    thread.start()
                    threads.append(thread)
                    time.sleep(0.1)  # Hindari CPU overload
            elif dataset.get('type') == 'serial':

                data_port = dataset.get('data_port')
                baudrate = dataset.get('baudrate')

                if not data_port or not baudrate:
                    signals.new_data_received.emit(f"Konfigurasi tidak valid: {dataset}")
                    continue

                thread = threading.Thread(target=receive_nmea_serial,
                                          args=(data_port, int(baudrate), stop_event, dataset.get('id')))
                if thread:
                    thread.start()
                    threads.append(thread)
                    time.sleep(1)
            else:
                signals.new_data_received.emit(f"Jenis dataset tidak valid: {dataset}")

        if not has_active_connection:
            signals.new_data_received.emit("⚠️ Tidak ada koneksi aktif! Menunggu stop_event...")
            while not stop_event.is_set():
                time.sleep(1)  # Biarkan berjalan agar bisa dihentikan
            signals.new_data_received.emit("Receiver dihentikan.")
        return threads

    except Exception as e:
        signals.new_data_received.emit(f"Error saat mengambil koneksi dari database: {e}")
        return []
