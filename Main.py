import threading
from receiver import receive_nmea_udp
from sender import send_ais_data
import time


if __name__ == "__main__":

    # Jalankan penerima data NMEA (UDP) di thread terpisah
    thread_receive = threading.Thread(target=receive_nmea_udp, daemon=True)
    thread_receive.start()

    # Jalankan pengiriman data AIS ke OpenCPN di thread terpisah
    thread_send = threading.Thread(target=send_ais_data, daemon=True)
    thread_send.start()

    # Kirim data AIS ke OpenCPN setiap 10 detik
    while True:
        send_ais_data()
        time.sleep(1)
