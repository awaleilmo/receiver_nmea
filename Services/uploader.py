import requests
import time
import json
from datetime import datetime, timedelta

from Controllers.NMEA_controller import get_pending_data, mark_data_as_sent
from Controllers.Configure_controller import get_config
from Services.SignalsMessages import signalsError, signalsWarning, signalsLogger
from Services.decoder import decode_ais
from requests.exceptions import RequestException, Timeout, ConnectionError
from Untils.logging_helper import sys_logger

API_URL = get_config()['api_server']
MAX_RETRIES = 3
TIMEOUT = 15
BATCH_SIZE = 100
RETRY_DELAY = 30

def send_batch_data(stop_event):
    retry_count = 0
    last_success_time = datetime.now()

    while not stop_event.is_set():
        try:
            if stop_event.is_set():
                break

            # 1. Get data from database
            data = get_pending_data(BATCH_SIZE)
            if not data:
                if wait_with_interrupt(stop_event, TIMEOUT):
                    continue
                else:
                    break

            sys_logger.info(f"📡 Processing {len(data)} records...")

            # 2. Process decoded data
            decoded_list, ids = process_data_batch(data, stop_event)
            if stop_event.is_set():
                continue

            if not decoded_list:
                if not wait_with_interrupt(stop_event, TIMEOUT):
                    break
                continue

            # 3. Send data to API
            if not send_to_api(decoded_list, ids, stop_event):
                retry_count = 0
            else:
                retry_count += 1
                if retry_count >= MAX_RETRIES:
                    sys_logger.info(f"📡 Too many consecutive failures, pausing...")
                    if not wait_with_interrupt(stop_event, RETRY_DELAY * 2):
                        break

            #4. Pause between batches
            if not wait_with_interrupt(stop_event, TIMEOUT):
                break

        except Exception as e:
            sys_logger.error(f"Unexpected error: {str(e)}")
            if not wait_with_interrupt(stop_event, RETRY_DELAY):
                break


def wait_with_interrupt(stop_event, timeout: int)->bool:
    """Sleep yang bisa diinterrupt"""
    for _ in range(timeout * 10):  # Check every 0.1 second
        if stop_event.is_set():
            return False
        time.sleep(0.1)
    return True


def process_data_batch(data, stop_event):
    """Proses data dengan pengecekan stop event"""
    decoded_list = []
    ids = []

    for record in data:
        if stop_event.is_set():
            return [], []

        try:
            decoded = decode_ais(record.nmea)
            if decoded:
                decoded['created_at'] = record.created_at.isoformat()
                decoded_list.append(decoded)
                ids.append(record.id)
        except Exception as e:
            sys_logger.warning(f"Decode error for record {record.id}: {str(e)}")

    return decoded_list, ids


def send_to_api(data, ids, stop_event):
    """Kirim data dengan timeout pendek dan interrupt"""
    for attempt in range(MAX_RETRIES):
        if stop_event.is_set():
            return False

        json_str = json.dumps(data, ensure_ascii=False)
        try:
            response = requests.post(
                API_URL,
                json=data,
                timeout=5,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code in (200, 201):
                mark_data_as_sent(ids)
                sys_logger.info(f"Successfully sent {len(ids)} records")
                return True
            else:
                sys_logger.error(f"API Error: HTTP {response.status_code}")
                if attempt == MAX_RETRIES - 1:
                    raise RequestException(f"API returned {response.status_code}")

        except (Timeout, ConnectionError) as e:
            sys_logger.warning(f"Network error (attempt {attempt + 1}): {str(e)}")
            if attempt == MAX_RETRIES - 1:
                raise
        except RequestException as e:
            sys_logger.error(f"Request failed: {str(e)}")
            raise

        if not wait_with_interrupt(stop_event, RETRY_DELAY):
            return False

    return False