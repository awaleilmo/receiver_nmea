import socket
import json
import time
import requests
import threading

import serial
import ais

from Controllers.NMEA_controller import save_nmea_data, batch_save_nmea
from Controllers.Configure_controller import get_config
from Controllers.Connection_controller import get_connection

from Services.SignalsMessages import signalsError, signalsInfo, signalsLogger

ais_buffer = {}

LARAVEL_API_URL = get_config()['api_server']

def receive_nmea_tcp(host, port, stop_event, connection_id):
    while not stop_event.is_set():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((host, port))
                sock.listen(1)
                signalsLogger.new_data_received.emit(f"Menunggu TCP data NMEA di {host}:{port}...")
                count = 0
                start_time = time.time()

                while not stop_event.is_set():
                    sock.settimeout(1.0)
                    try:
                        conn, addr = sock.accept()
                        with conn:
                            buffer = conn.recv(4096).decode("utf-8", errors="ignore")
                            count += 1
                            nmea_data = buffer
                            batch_save_nmea(buffer, connection_id)

                        if time.time() - start_time >= 60:
                            signalsInfo.new_data_received.emit(f"Total data diterima dari TCP dalam 1 menit: {count}")
                            count = 0
                            start_time = time.time()

                    except socket.timeout:
                        continue
        except Exception as e:
            signalsError.new_data_received.emit(f"TCP ERROR: {e}")
            time.sleep(10)
        finally:
            signalsInfo.new_data_received.emit("Receiver stopped.")

def receive_nmea_udp(host, port, stop_event, connection_id):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        sock.bind((host, port))
        signalsLogger.new_data_received.emit(f"Menunggu UDP data NMEA di {host}:{port}...")

        count = 0
        start_time = time.time()

        while not stop_event.is_set():
            try:
                sock.settimeout(1.0)
                data, addr = sock.recvfrom(1024)
                count += 1

                if time.time() - start_time >= 60:
                    signalsInfo.new_data_received.emit(f"Total data diterima dari UDP dalam 1 menit: {count}")
                    count = 0
                    start_time = time.time()

                nmea_data = data.decode("utf-8", errors="ignore")
                batch_save_nmea(nmea_data, connection_id)

            except socket.timeout:
                continue
            except Exception as e:
                signalsError.new_data_received.emit(f"UDP ERROR: {e}")

def receive_nmea_serial(port, baudrate, stop_event, connection_id):
    ser = None

    while not stop_event.is_set():
        try:
            ser = serial.Serial(port=port, baudrate=baudrate, timeout=0.5, exclusive=True)
            signalsLogger.new_data_received.emit(f"Menunggu Serial data NMEA dari {port}...")
            buffer = ""
            start_time = time.time()
            count = 0

            while not stop_event.is_set():
                if ser.in_waiting:
                    buffer += ser.read(ser.in_waiting).decode("utf-8", errors="ignore")

                if "\n" in buffer:
                    batch_save_nmea(buffer, connection_id)
                    count += 1
                    buffer = ""

                if time.time() - start_time >= 60:
                    signalsInfo.new_data_received.emit(f"Total data diterima dari Serial dalam 1 menit: {count}")
                    count = 0
                    start_time = time.time()

                time.sleep(0.05)
        except serial.SerialException as e:
            signalsError.new_data_received.emit(f"Gagal membuka {port}: {e}")
            time.sleep(10)

        except Exception as e:
            signalsError.new_data_received.emit(f"Serial ERROR: {e}")

        finally:
            if ser is not None:
                try:
                    if ser.is_open:
                        ser.close()
                        signalsInfo.new_data_received.emit(f"Port {port} ditutup.")
                except Exception as e:
                    signalsError.new_data_received.emit(f"Error saat menutup serial {port}: {e}")

    signalsInfo.new_data_received.emit("Receiver serial stopped.")

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
                thread = None

                protocol = dataset.get('network')
                address = dataset.get('address')
                port = dataset.get('port')

                if not address or not port:
                    signalsError.new_data_received.emit(f"Konfigurasi tidak valid: {dataset}")
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
                    time.sleep(0.1)
            elif dataset.get('type') == 'serial':

                data_port = dataset.get('data_port')
                baudrate = dataset.get('baudrate')

                if not data_port or not baudrate:
                    signalsError.new_data_received.emit(f"Konfigurasi tidak valid: {dataset}")
                    continue

                thread = threading.Thread(target=receive_nmea_serial,
                                          args=(data_port, int(baudrate), stop_event, dataset.get('id')))
                if thread:
                    thread.start()
                    threads.append(thread)
                    time.sleep(1)
            else:
                signalsError.new_data_received.emit(f"Jenis dataset tidak valid: {dataset}")

        if not has_active_connection:
            signalsInfo.new_data_received.emit("⚠️ Tidak ada koneksi aktif! Menunggu stop_event...")
            while not stop_event.is_set():
                time.sleep(1)
            signalsInfo.new_data_received.emit("Receiver dihentikan.")
        return threads

    except Exception as e:
        signalsError.new_data_received.emit(f"Error saat mengambil koneksi dari database: {e}")
        return []
