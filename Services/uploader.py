import requests
import time

from Controllers.NMEA_controller import get_pending_data, mark_data_as_sent
from Controllers.Configure_controller import get_config
from Services.SignalsMessages import signalsError, signalsWarning, signalsLogger
from Services.decoder import decode_ais

API_URL = get_config()['api_server']

timerSleep = 15

def send_batch_data(stop_event):
    """Mengirimkan data AIS dalam batch maksimal 350 data setiap 30 detik."""
    while not stop_event.is_set():
        data = get_pending_data(100)  # Ambil 350 data yang belum terkirim

        if not data:
            signalsWarning.new_data_received.emit("⚠️ Tidak ada data NMEA untuk dikirim.")
            time.sleep(timerSleep)
            continue

        signalsWarning.new_data_received.emit(f"📡 Mengambil data NMEA untuk dikirim...")

        decoded_list = []
        ids = []

        for record in data:
            decoded_data = decode_ais(record.nmea)  # Decode AIS

            if decoded_data:
                decoded_data['created_at'] = record.created_at.isoformat()
                decoded_list.append(decoded_data)
                ids.append(record.id)

        if not decoded_list:
            time.sleep(timerSleep)
            continue

        try:
            response = requests.post(API_URL, json=decoded_list, timeout=10)

            if response.status_code in [200, 201]:
                print("🔄 Marking sent data in database...")
                mark_data_as_sent(ids)
                signalsLogger.new_data_received.emit(f"✅ {len(ids)} data berhasil dikirim ke API")
            else:
                signalsWarning.new_data_received.emit(f"⚠️ Gagal mengirim data: {response.status_code} - {response.text}")

        except requests.exceptions.RequestException as e:
            signalsError.new_data_received.emit(f"🚨 Koneksi ke API gagal")

        time.sleep(timerSleep)  # Kirim data setiap 30 detik
