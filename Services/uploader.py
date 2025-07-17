import requests
import time
import json
from datetime import datetime, timedelta

from Controllers.NMEA_controller import get_pending_data, mark_data_as_sent, mark_data_as_failed, get_pending_count
from Services.SignalsMessages import signalsError, signalsWarning, signalsLogger
from Services.decoder import decode_ais
from requests.exceptions import RequestException, Timeout, ConnectionError
from Untils.logging_helper import sys_logger
import configparser
from Untils.path_helper import get_resource_path

config_path = get_resource_path("config.ini", is_config=True)
config = configparser.ConfigParser()
config.read(config_path)

API_URL = config['API']['AIS']
MAX_RETRIES = 3
TIMEOUT = 15
BATCH_SIZE = 5000
RETRY_DELAY = 30

def send_batch_data(stop_event):
    retry_count = 0
    last_success_time = datetime.now()

    sys_logger.info(f'{API_URL}')

    while not stop_event.is_set():
        try:
            if stop_event.is_set():
                break

            # 1. Get data from database
            data = get_pending_data(BATCH_SIZE)
            if not data:
                sys_logger.info("No pending data, waiting...")
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
                sys_logger.info("No decodable data in this batch, waiting...")
                if not wait_with_interrupt(stop_event, TIMEOUT):
                    break
                continue

            # 3. Send data to API
            success = send_to_api(decoded_list, ids, stop_event)

            if success:
                # Reset retry count on success
                retry_count = 0
                last_success_time = datetime.now()
            else:
                retry_count += 1
                if retry_count >= MAX_RETRIES:
                    sys_logger.warning(f"📡 Too many consecutive failures ({retry_count}), pausing for {RETRY_DELAY * 2} seconds...")
                    if not wait_with_interrupt(stop_event, RETRY_DELAY * 2):
                        break
                    # Reset retry count after pausing
                    retry_count = 0

            # Check for long periods without successful sends
            time_since_last_success = datetime.now() - last_success_time
            if time_since_last_success > timedelta(minutes=5):
                sys_logger.warning(f"No successful API transmission for {time_since_last_success.total_seconds() // 60} minutes")
                last_success_time = datetime.now()  # Reset to prevent spamming logs

            #4. Pause between batches
            if not wait_with_interrupt(stop_event, TIMEOUT):
                break

        except Exception as e:
            sys_logger.error(f"Unexpected error in send_batch_data: {str(e)}")
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
    total_processed = 0
    total_skipped = 0

    for record in data:
        if stop_event.is_set():
            return [], []

        try:
            decoded = decode_ais(record.nmea)
            if decoded:
                decoded['created_at'] = record.created_at.isoformat()
                decoded_list.append(decoded)
                ids.append(record.id)
                total_processed += 1
            else:
                total_skipped += 1
        except Exception as e:
            sys_logger.warning(f"Decode error for record {record.id}: {str(e)}")
            total_skipped += 1

    if total_processed > 0 or total_skipped > 0:
        sys_logger.info(f"Processed {total_processed} records, skipped {total_skipped} records")

    return decoded_list, ids


def send_to_api(data, ids, stop_event):
    """Kirim data dengan timeout pendek dan interrupt"""
    if not data:
        sys_logger.warning("No data to send to API")
        return False

    for attempt in range(MAX_RETRIES):
        if stop_event.is_set():
            return False

        try:
            response = requests.post(
                API_URL,
                json=data,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )

            # Log API response details
            sys_logger.info(f"API Response: Status {response.status_code}, Content: {response.text[:200]}")

            if response.status_code in (200, 201):
                mark_data_as_sent(ids)
                sys_logger.info(f"Successfully sent {len(ids)} records")
                return True
            else:
                sys_logger.error(f"API Error: HTTP {response.status_code}, Response: {response.text[:200]}")
                if attempt == MAX_RETRIES - 1:
                    raise RequestException(f"API returned {response.status_code}: {response.text[:200]}")

        except (Timeout, ConnectionError) as e:
            sys_logger.warning(f"Network error (attempt {attempt + 1}/{MAX_RETRIES}): {str(e)}")
            if attempt == MAX_RETRIES - 1:
                raise
        except RequestException as e:
            sys_logger.error(f"Request failed: {str(e)}")
            raise
        except Exception as e:
            sys_logger.error(f"Unexpected error in API communication: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                raise

        # Retry after delay
        sys_logger.info(f"Retrying API call in {RETRY_DELAY} seconds (attempt {attempt + 1}/{MAX_RETRIES})...")
        if not wait_with_interrupt(stop_event, RETRY_DELAY):
            return False

    return False