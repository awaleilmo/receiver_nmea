import requests
import time
import json
from datetime import datetime, timedelta

from Controllers.NMEA_controller import get_historical_pending_data, mark_data_as_sent, mark_data_as_failed, \
    get_historical_pending_count, get_old_data_stats
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
BATCH_SIZE = 10000
RETRY_DELAY = 30
MAX_CONSECUTIVE_FAILED_BATCHES = 5

# In-memory tracking untuk session ini (tidak persisten)
_session_failed_ids = set()
_session_stats = {
    'total_processed': 0,
    'total_decoded': 0,
    'total_failed': 0,
    'total_sent': 0,
    'start_time': datetime.now()
}

def send_batch_data(stop_event):
    retry_count = 0
    last_success_time = datetime.now()
    consecutive_failed_batches = 0

    global _session_stats
    _session_stats['start_time'] = datetime.now()

    while not stop_event.is_set():
        try:
            if stop_event.is_set():
                break

            # 1. Check total pending data
            total_pending = get_historical_pending_count()
            sys_logger.info(f"📊 Total pending data in database: {total_pending}")

            # 2. Get data from database
            data = get_historical_pending_data(BATCH_SIZE)
            if not data:
                sys_logger.info("No more pending data for Old data, upload complete!")
                if wait_with_interrupt(stop_event, TIMEOUT):
                    continue
                else:
                    break

            sys_logger.info(f"📡 Processing {len(data)} records from old data...")

            # 3. Process decoded data with better tracking
            decoded_list, successful_ids, failed_ids = process_data_batch_enhanced(data, stop_event)
            if stop_event.is_set():
                continue

            #4. handle failed decoded data
            if failed_ids:
                sys_logger.warning(f"⚠️ {len(failed_ids)} records failed to decode, marking as failed")

                new_failed_ids, repeated_failed_ids = []

                for fid in failed_ids:
                    if fid not in _session_failed_ids:
                        repeated_failed_ids.append(fid)
                    else:
                        new_failed_ids.append(fid)
                        _session_failed_ids.add(fid)

                if repeated_failed_ids:
                    sys_logger.warning(f"🚨 {len(repeated_failed_ids)} records for old data were repeatedly failed, marking as permanently failed")
                    try:
                        mark_data_as_failed(repeated_failed_ids, '"decode_failed_today')
                    except Exception as e:
                        sys_logger.error(f"Error marking repeated failed data: {str(e)}")

                if new_failed_ids:
                    sys_logger.info(f"📝 {len(new_failed_ids)} new failures, will retry in next batch")

            #5. Send decodable data to API
            if not decoded_list:
                sys_logger.info(f"🚀 Attempting to send {len(decoded_list)} old data's records to API")
                success = send_to_api(decoded_list, successful_ids, stop_event)
                if success:
                    retry_count = 0
                    consecutive_failed_batches = 0
                    last_success_time = datetime.now()

                    _session_stats['total_sent'] += len(successful_ids)

                    sys_logger.info(f"✅ Successfully sent {len(successful_ids)} records to API")

                    log_session_stats()
                else:
                    consecutive_failed_batches += 1
                    retry_count += 1

                    if retry_count >= MAX_RETRIES:
                        sys_logger.warning(f"📡 Too many consecutive failures ({retry_count}), pausing for {RETRY_DELAY * 2} seconds...")
                        if not wait_with_interrupt(stop_event, RETRY_DELAY * 2):
                            break
                        retry_count = 0

            else:
                if failed_ids:
                    sys_logger.warning(f"❌ No decodable data in this batch, all records failed decode")
                else:
                    sys_logger.info(f"ℹ️ No Data to process in this batch")
                consecutive_failed_batches = 0

            #6. check for too many consecutive failed batches
            if consecutive_failed_batches >= MAX_CONSECUTIVE_FAILED_BATCHES:
                sys_logger.warning(f"🚨 Too many consecutive failed batches ({consecutive_failed_batches}), pausing for {RETRY_DELAY * 2} seconds...")
                if not wait_with_interrupt(stop_event, RETRY_DELAY * 2):
                    break
                consecutive_failed_batches = 0

            #7. check for long periods without successful sends
            time_since_last_success = datetime.now() - last_success_time
            if time_since_last_success > timedelta(minutes=5):
                sys_logger.warning(f"No successful API transmission for {time_since_last_success.total_seconds() // 60} minutes")
                last_success_time = datetime.now()

            #8. Pause between batches
            if not wait_with_interrupt(stop_event, TIMEOUT):
                break

        except Exception as e:
            sys_logger.error(f"💥 Unexpected error in send_batch_data: {str(e)}")
            consecutive_failed_batches += 1
            if not wait_with_interrupt(stop_event, RETRY_DELAY):
                break
    log_session_stats(final=True)

def process_data_batch_enhanced(data, stop_event):
    """Proses data dengan pengecekan stop event"""
    decoded_list = []
    successful_ids = []
    failed_ids = []

    global _session_stats
    _session_stats['total_processed'] += len(data)

    for record in data:
        if stop_event.is_set():
            return [], [], []

        try:
            # Convert dict to object-like structure
            class RecordObj:
                def __init__(self, data_dict):
                    for key, value in data_dict.items():
                        setattr(self, key, value)

            record_obj = RecordObj(record)

            if len(decoded_list) < 3:
                sys_logger.info(f"🔍 Processing sample {len(decoded_list) + 1}: {record_obj.nmea[:60]}...")

            decoded = decode_ais(record_obj.nmea)
            if decoded:
                decoded['created_at'] = record_obj.created_at.isoformat() if hasattr(record_obj.created_at, 'isoformat') else str(record_obj.created_at)
                decoded_list.append(decoded)
                successful_ids.append(record_obj.id)

                if len(decoded_list) <= 3:
                    sys_logger.info(f"✅ Decoded successfully: Message type {decoded.get('msg_type', 'unknown')}")
            else:
                failed_ids.append(record_obj.id)
                if len(failed_ids) <= 3:
                    sys_logger.warning(f"❌ Failed to decode: {record_obj.nmea[:60]}...")

        except Exception as e:
            sys_logger.error(f"💥 Decode error for record {record.get('id', 'unknown')}: {str(e)}")
            failed_ids.append(record.get('id'))

    _session_stats['total_decoded'] += len(decoded_list)
    _session_stats['total_failed'] += len(failed_ids)

    decode_rate = (len(successful_ids) / len(data)) * 100 if data else 0
    sys_logger.info(f"📊 Batch result: {len(successful_ids)} decoded ({decode_rate:.1f}%), {len(failed_ids)} failed")

    return decoded_list, successful_ids, failed_ids

def send_to_api(data, ids, stop_event):
    """Kirim data dengan timeout pendek dan interrupt"""
    if not data:
        sys_logger.warning("No data to send to API")
        return False

    for attempt in range(MAX_RETRIES):
        if stop_event.is_set():
            return False

        try:
            sys_logger.info(f"🚀 Sending {len(data)} records to API (attempt {attempt + 1}/{MAX_RETRIES})")

            response = requests.post(
                API_URL,
                json=data,
                timeout=15,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code in (200, 201):
                mark_data_as_sent(ids)
                return True
            else:
                response_text = response.text[:200] if response.text else "No response body"
                sys_logger.error(f"❌ API Error: HTTP {response.status_code}, Response: {response_text}")

                if response.status_code >= 500:
                    # Server error, retry
                    continue
                else:
                    # Client error, don't retry
                    return False

        except (Timeout, ConnectionError) as e:
            sys_logger.warning(f"Network error (attempt {attempt + 1}/{MAX_RETRIES}): {str(e)}")
            if attempt == MAX_RETRIES - 1:
                return False
        except RequestException as e:
            sys_logger.error(f"Request failed: {str(e)}")
            return False
        except Exception as e:
            sys_logger.error(f"Unexpected error in API communication: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                return False

        # Retry after delay
        if attempt < MAX_RETRIES - 1:
            sys_logger.info(f"⏳ Retrying API call in {RETRY_DELAY} seconds...")
            if not wait_with_interrupt(stop_event, RETRY_DELAY):
                return False

    return False

def wait_with_interrupt(stop_event, timeout: int) -> bool:
    """Sleep yang bisa diinterrupt"""
    for _ in range(timeout * 10):  # Check every 0.1 second
        if stop_event.is_set():
            return False
        time.sleep(0.1)
    return True

def log_session_stats(final=False):
    global _session_stats

    runtime = datetime.now() - _session_stats['start_time']
    runtime_minutes = runtime.total_seconds() / 60

    if final:
        sys_logger.info("📊 FINAL SESSION STATISTICS:")
    else:
        sys_logger.info("📊 SESSION STATISTICS:")

    sys_logger.info(f"   Runtime: {runtime_minutes:.1f} minutes")
    sys_logger.info(f"   Total processed: {_session_stats['total_processed']:,}")
    sys_logger.info(f"   Successfully decoded: {_session_stats['total_decoded']:,}")
    sys_logger.info(f"   Failed decode: {_session_stats['total_failed']:,}")
    sys_logger.info(f"   Sent to API: {_session_stats['total_sent']:,}")

    if _session_stats['total_processed'] > 0:
        decode_rate = (_session_stats['total_decoded'] / _session_stats['total_processed']) * 100
        sys_logger.info(f"   Overall decode rate: {decode_rate:.1f}%")

    if runtime_minutes > 0:
        processing_rate = _session_stats['total_processed'] / runtime_minutes
        sys_logger.info(f"   Processing rate: {processing_rate:.1f} records/minute")

def get_session_stats():
    """Ambil statistik session saat ini"""
    return _session_stats.copy()