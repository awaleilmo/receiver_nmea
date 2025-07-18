import ais
import time
import json
import re

from Untils.logging_helper import sys_logger

ais_buffer = {}
ais_buffer_time = {}

# Production-safe error tracking (in-memory only)
_decode_stats = {
    'total_attempts': 0,
    'successful_decodes': 0,
    'failed_decodes': 0,
    'error_types': {},
    'start_time': time.time()
}

def try_decode(payload):
    try:
        msg_type = int(payload[:6], 2)
    except ValueError:
        msg_type = 0

    if msg_type in {5, 19, 21, 24}:
        versions = [2, 0, 1]
    else:
        versions = [0, 1, 2]

    for version in versions:
        try:
            decoded_messages = ais.decode(payload, version)
            if isinstance(decoded_messages, list) and len(decoded_messages) > 0:
                return decoded_messages[0], version
            return decoded_messages, version
        except Exception as e:
            continue
    return None, None

def decode_ais(nmea_sentence):

    global _decode_stats
    _decode_stats['total_attempts'] += 1

    try:
        # Validasi format NMEA dasar
        if not nmea_sentence or not isinstance(nmea_sentence, str):
            _track_error("invalid_input_type")
            return None

        nmea_sentence = nmea_sentence.strip()

        if not (nmea_sentence.startswith("!AIVDM") or nmea_sentence.startswith("!AIVDO")):
            _track_error("not_ais_sentence")
            return None

        parts = nmea_sentence.split(",")

        if len(parts) <= 5:
            _track_error("invalid_nmea_format")
            return None

        try:
            fragment_count = int(parts[1])
            fragment_number = int(parts[2])
            message_id = parts[3]
            channel = parts[4]
            payload = parts[5]
        except (ValueError, IndexError):
            _track_error("invalid_nmea_fields")
            return None

        # Validasi payload
        if not payload or len(payload) < 6:
            _track_error("invalid_payload_length")
            return None

        # Validasi karakter payload (harus valid 6-bit ASCII)
        if not re.match(r'^[0-9:;<=>?@A-Z\[\\\]^_`a-w]*$', payload):
            _track_error("invalid_payload_characters")
            return None

        unique_key = f"{message_id}_{channel}"

        if fragment_count == 1:
            # Single fragment message
            decoded_data, version = try_decode(payload)
            if not decoded_data:
                _track_error("decode_failed_single")
                return None

            if isinstance(decoded_data, dict):
                decoded_data["channel"] = channel
                decoded_data["message_id"] = message_id
                decoded_data["fragment_count"] = fragment_count
                decoded_data["decoder_version"] = version

            _decode_stats['successful_decodes'] += 1
            return decoded_data

        # Multi-fragment message handling
        if unique_key not in ais_buffer:
            ais_buffer[unique_key] = [""] * fragment_count
            ais_buffer[unique_key + "_received"] = set()
            ais_buffer_time[unique_key] = time.time()

        ais_buffer[unique_key][fragment_number - 1] = payload
        ais_buffer[unique_key + "_received"].add(fragment_number)

        if len(ais_buffer[unique_key + "_received"]) == fragment_count:
            # All fragments received
            full_payload = "".join(ais_buffer.pop(unique_key))
            ais_buffer.pop(unique_key + "_received")
            ais_buffer_time.pop(unique_key, None)

            try:
                decoded_data, version = try_decode(full_payload)

                if not decoded_data:
                    _track_error("decode_failed_multi")
                    return None

                if isinstance(decoded_data, dict):
                    decoded_data["channel"] = channel
                    decoded_data["message_id"] = message_id
                    decoded_data["fragment_count"] = fragment_count
                    decoded_data["decoder_version"] = version

                _decode_stats['successful_decodes'] += 1
                return decoded_data

            except Exception as e:
                _track_error(f"decode_exception_{type(e).__name__}")
                return None

        # Clean up old incomplete messages
        current_time = time.time()
        current_keys = []
        for key, timestamp in ais_buffer_time.items():
            if current_time - timestamp > 60:  # Remove messages older than 60 seconds
                current_keys.append(key)

        for key in current_keys:
            ais_buffer.pop(key, None)
            ais_buffer.pop(key + "_received", None)
            ais_buffer_time.pop(key, None)

        # Waiting for more fragments
        return None

    except Exception as e:
        _track_error(f"general_exception_{type(e).__name__}")
        sys_logger.error(f"Decode error: {str(e)} for sentence: {nmea_sentence[:50] if nmea_sentence else 'None'}")
        return None

def _track_error(error_type):
    """Track error types for diagnostics (in-memory only)"""
    global _decode_stats
    _decode_stats['failed_decodes'] += 1

    if error_type not in _decode_stats['error_types']:
        _decode_stats['error_types'][error_type] = 0
    _decode_stats['error_types'][error_type] += 1

def get_decode_statistics():
    global _decode_stats

    stats = _decode_stats.copy()

    if stats['total_attempts'] > 0:
        stats['success_rate'] = (stats['successful_decodes'] / stats['total_attempts']) * 100
        stats['failure_rate'] = (stats['failed_decodes'] / stats['total_attempts']) * 100
    else:
        stats['success_rate'] = 0
        stats['failure_rate'] = 0

    # Runtime
    stats['runtime_seconds'] = time.time() - stats['start_time']

    return stats

def reset_decode_statistics():
    """Reset decode statistics"""
    global _decode_stats
    _decode_stats = {
        'total_attempts': 0,
        'successful_decodes': 0,
        'failed_decodes': 0,
        'error_types': {},
        'start_time': time.time()
    }

def log_decode_statistics():
    """Log current decode statistics"""
    stats = get_decode_statistics()

    sys_logger.info("🔍 DECODE STATISTICS:")
    sys_logger.info(f"   Total attempts: {stats['total_attempts']:,}")
    sys_logger.info(f"   Successful: {stats['successful_decodes']:,}")
    sys_logger.info(f"   Failed: {stats['failed_decodes']:,}")
    sys_logger.info(f"   Success rate: {stats['success_rate']:.1f}%")
    sys_logger.info(f"   Runtime: {stats['runtime_seconds'] / 60:.1f} minutes")

    if stats['error_types']:
        sys_logger.info("   Top error types:")
        sorted_errors = sorted(stats['error_types'].items(), key=lambda x: x[1], reverse=True)
        for error_type, count in sorted_errors[:5]:  # Top 5
            sys_logger.info(f"     {error_type}: {count:,}")

def cleanup_old_fragments():
    """Cleanup old incomplete fragments"""
    current_time = time.time()
    cleanup_keys = []

    for key, timestamp in ais_buffer_time.items():
        if current_time - timestamp > 300:  # 5 minutes timeout
            cleanup_keys.append(key)

    for key in cleanup_keys:
        ais_buffer.pop(key, None)
        ais_buffer.pop(key + "_received", None)
        ais_buffer_time.pop(key, None)

    if cleanup_keys:
        sys_logger.info(f"🧹 Cleaned up {len(cleanup_keys)} old incomplete fragments")

def get_buffer_status():
    """Get current buffer status"""
    return {
        'incomplete_messages': len(ais_buffer_time),
        'oldest_fragment_age': (time.time() - min(ais_buffer_time.values())) if ais_buffer_time else 0,
        'buffer_keys': list(ais_buffer_time.keys())
    }