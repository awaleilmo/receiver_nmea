import socket
import time
import threading
from Controllers.Sender_controller import get_sender, update_sender_last_send_id
from Controllers.NMEA_controller import get_ais_latest
from Services.SignalsMessages import signalsInfo, signalsError, signalsLogger


def sender_udp(host, port, last_id, identity, stop_event):
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    last_send_id = last_id

    signalsInfo.new_data_received.emit(f"Sender UDP {host}:{port} started...")

    while not stop_event.is_set():
        try:
            new_data = get_ais_latest(last_send_id)

            if new_data:
                count = 0
                for data_id, nmea in new_data:
                    udp_socket.sendto(nmea.encode("utf-8"), (host, port))
                    last_send_id = data_id
                    count += 1

                signalsLogger.new_data_received.emit(f"Berhasil mengirim {count} data ke {host}:{port}")
                update_sender_last_send_id(identity, last_send_id)

            time.sleep(1.0)

        except Exception as e:
            signalsError.new_data_received.emit(f"Sender error: {e}")
            time.sleep(10)

    udp_socket.close()
    signalsInfo.new_data_received.emit("Sender stopped.")


def sender_tcp(host, port, last_id, identity, stop_event):
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    last_send_id = last_id

    signalsInfo.new_data_received.emit(f"Sender TCP {host}:{port} started...")

    while not stop_event.is_set():
        try:
            new_data = get_ais_latest(last_send_id)

            if new_data:
                count = 0
                for data_id, nmea in new_data:
                    tcp_socket.connect((host, port))
                    tcp_socket.send(nmea.encode("utf-8"))
                    last_send_id = data_id
                    count += 1

                signalsLogger.new_data_received.emit(f"Berhasil mengirim {count} data ke {host}:{port}")
                update_sender_last_send_id(identity, last_send_id)

            time.sleep(1.0)

        except Exception as e:
            signalsError.new_data_received.emit(f"Sender error: {e}")
            time.sleep(10)

    tcp_socket.close()
    signalsInfo.new_data_received.emit("Sender stopped.")


def start_multiple_senders(stop_event):
    try:
        sender_configs = get_sender()
        threads = []

        if not sender_configs:
            signalsInfo.new_data_received.emit("No sender configurations found")
            return threads  # Return empty list

        has_active_sender = False

        for sender_config in sender_configs:
            if sender_config.get('active') != 1:
                continue

            has_active_sender = True
            thread = None

            try:

                if sender_config['network'] == 'udp':
                    thread = threading.Thread(target=sender_udp,
                                              args=(sender_config['host'], int(sender_config['port']),
                                                    sender_config['last_send_id'], sender_config['id'],
                                                    stop_event),
                                              daemon=True
                                              )
                elif sender_config['type'] == 'tcp':
                    thread = threading.Thread(target=sender_tcp,
                                              args=(sender_config['host'], int(sender_config['port']),
                                                    sender_config['last_send_id'], sender_config['id'],
                                                    stop_event),
                                              daemon=True
                                              )

                if thread is not None:
                    thread.start()
                    threads.append(thread)
                    time.sleep(0.1)
            except KeyError as e:
                signalsError.new_data_received.emit(
                    f"Invalid sender config - missing {str(e)}"
                )
                continue

        if not has_active_sender:
            signalsInfo.new_data_received.emit("Tidak ada sender aktif")

        return threads
    except Exception as e:
        signalsError.new_data_received.emit(f"Sender initialization error: {e}")
        return []
