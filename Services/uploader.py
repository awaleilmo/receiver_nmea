import requests
import time

from Controllers.NMEA_controller import get_pending_data, mark_data_as_sent
from Controllers.Configure_controller import get_config
from Services.SignalsMessages import signalsError, signalsWarning, signalsLogger
from Services.decoder import decode_ais

API_URL = get_config().get('api_server','')
MAX_RETRIES = 3
TIMEOUT = 15
BATCH_SIZE = 100
RETRY_DELAY = 30

def send_batch_data(stop_event):
    """Mengirimkan data AIS dalam batch maksimal 350 data setiap 30 detik."""
    retry_count = 0
    last_success_time = datetime.now()

    while not stop_event.is_set():
        try:
            data = get_pending_data(BATCH_SIZE)

            if not data:
                if retry_count == 0:
                    signalsLogger.new_data_received.emit("ℹ️ Tidak ada data pending")
                time.sleep(TIMEOUT)
                continue

            signalsWarning.new_data_received.emit(f"📡 Memproses {len(data)} data...")

            decoded_list = []
            ids = []
            decode_errors = 0

            for record in data:
                try:
                    decoded_data = decode_ais(record.nmea)  # Decode AIS
                    if decoded_data:
                        decoded_data['created_at'] = record.created_at.isoformat()
                        decoded_list.append(decoded_data)
                        ids.append(record.id)
                except Exception as e:
                    decode_errors += 1
                    signalsError.new_data_received.emit(f"Decode error on record {record.id}: {str(e)}")

            if decode_errors:
                signalsError.new_data_received.emit(f"⚠️ {decode_errors} data gagal didecode")

            if not decoded_list:
                time.sleep(TIMEOUT)
                continue

            for attempt in range(MAX_RETRIES):
                try:
                    response = requests.post(
                        API_URL,
                        json=decoded_list,
                        timeout=10,
                        headers={'Content-Type': 'application/json'}
                    )

                    if response.status_code in [200, 201]:
                        mark_data_as_sent(ids)
                        signalsLogger.new_data_received.emit(
                            f"✅ {len(ids)} data berhasil dikirim (Attempt {attempt + 1})"
                        )
                        last_success_time = datetime.now()
                        retry_count = 0
                        break
                    else:
                        signalsWarning.new_data_received.emit(
                            f"⚠️ Gagal mengirim data (Status {response.status_code})"
                        )

                except requests.exceptions.RequestException as e:
                    if attempt == MAX_RETRIES - 1:
                        signalsError.new_data_received.emit("🚨 Gagal setelah 3 percobaan")
                    time.sleep(RETRY_DELAY)

            time.sleep(TIMEOUT)  # Kirim data setiap 30 detik

        except Exception as e:
            signalsError.new_data_received.emit(f"🚨 Error sistem upload")
            time.sleep(RETRY_DELAY)
