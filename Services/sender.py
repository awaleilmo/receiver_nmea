import socket
import time
from Controllers.Configure_controller import get_config
from Controllers.NMEA_controller import get_ais_latest
from Services.SignalsMessages import signalsInfo, signalsError, signalsLogger

config = get_config()
UDP_IP = config['cpn_host']
UDP_PORT = int(config['cpn_port'])

def send_ais_data(stop_event):
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    signalsInfo.new_data_received.emit(f"Sender started...")
    try:
        while not stop_event.is_set():
            ais_data = get_ais_latest()
            for nmea_sentence in ais_data:
                udp_socket.sendto(nmea_sentence.encode("utf-8"), (UDP_IP, UDP_PORT))
                signalsLogger.new_data_received.emit(f"Mengirim ke {UDP_IP}:{UDP_PORT}: {nmea_sentence}")
            time.sleep(2)  # Tunggu sebelum mengirim ulang

    except Exception as e:
        signalsError.new_data_received.emit(f"Sender error: {e}")

    finally:
        udp_socket.close()  # Pastikan socket ditutup saat berhenti
        signalsInfo.new_data_received.emit("Sender stopped.")
