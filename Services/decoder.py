import ais
import time
import json
import re

from Untils.logging_helper import sys_logger

ais_buffer = {}
ais_buffer_time = {}


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
            sys_logger.error(f"Failed to decode with version {version}: {str(e)}")
            continue
    return None, None

def decode_ais(nmea_sentence):
    try:
        if not nmea_sentence or not isinstance(nmea_sentence, str):
            sys_logger.warning(f"Invalid NMEA sentence type: {type(nmea_sentence)}")
            return None

        if not (nmea_sentence.startswith("!AIVDM") or nmea_sentence.startswith("!AIVDO")):
            sys_logger.warning(f"Not an AIS sentence: {nmea_sentence[:20]}...")
            return None

        parts = nmea_sentence.split(",")

        if len(parts) <= 5:
            sys_logger.debug(f"Invalid NMEA format, not enough parts: {len(parts)}")
            return None

        fragment_count = int(parts[1])
        fragment_number = int(parts[2])
        message_id = parts[3]
        channel = parts[4]
        payload = parts[5]

        # Validasi payload
        if not payload or len(payload) < 6:
            sys_logger.debug(f"Invalid payload length: {len(payload) if payload else 0}")
            return None

        unique_key = f"{message_id}_{channel}"

        if fragment_count == 1:
            # Single fragment message
            sys_logger.debug(f"Processing single fragment: {nmea_sentence[:50]}...")
            decoded_data, version = try_decode(payload)
            if not decoded_data:
                sys_logger.debug(f"Failed to decode single fragment: {payload[:20]}...")
                return None

            if isinstance(decoded_data, dict):
                decoded_data["channel"] = channel
                decoded_data["message_id"] = message_id
                decoded_data["fragment_count"] = fragment_count
                sys_logger.debug(f"Successfully decoded single fragment, msg_type: {decoded_data.get('msg_type', 'unknown')}")

            return decoded_data

        # Multi-fragment message handling
        if unique_key not in ais_buffer:
            ais_buffer[unique_key] = [""] * fragment_count
            ais_buffer[unique_key + "_received"] = set()
            ais_buffer_time[unique_key] = time.time()
            sys_logger.debug(f"Started multi-fragment message: {unique_key}, expecting {fragment_count} fragments")

        ais_buffer[unique_key][fragment_number - 1] = payload
        ais_buffer[unique_key + "_received"].add(fragment_number)

        sys_logger.debug(f"Received fragment {fragment_number}/{fragment_count} for {unique_key}")

        if len(ais_buffer[unique_key + "_received"]) == fragment_count:
            # All fragments received
            full_payload = "".join(ais_buffer.pop(unique_key))
            ais_buffer.pop(unique_key + "_received")
            ais_buffer_time.pop(unique_key, None)

            sys_logger.debug(f"All fragments received for {unique_key}, decoding full payload...")

            try:
                decoded_data, version = try_decode(full_payload)

                if not decoded_data:
                    sys_logger.debug(f"Failed to decode complete multi-fragment: {full_payload[:20]}...")
                    return None

                if isinstance(decoded_data, dict):
                    decoded_data["channel"] = channel
                    decoded_data["message_id"] = message_id
                    decoded_data["fragment_count"] = fragment_count
                    sys_logger.debug(f"Successfully decoded multi-fragment, msg_type: {decoded_data.get('msg_type', 'unknown')}")

                return decoded_data

            except Exception as e:
                sys_logger.debug(f"Error decoding multi-fragment {unique_key}: {str(e)}")
                return None

        # Clean up old incomplete messages
        if time.time() - ais_buffer_time.get(unique_key, 0) > 60:
            sys_logger.debug(f"Cleaning up expired multi-fragment: {unique_key}")
            ais_buffer.pop(unique_key, None)
            ais_buffer.pop(unique_key + "_received", None)
            ais_buffer_time.pop(unique_key, None)
            return None

        # Waiting for more fragments
        sys_logger.debug(f"Waiting for more fragments for {unique_key}: {len(ais_buffer[unique_key + '_received'])}/{fragment_count}")
        return None

    except Exception as e:
        sys_logger.error(f"Failed to decode: {nmea_sentence[:50] if nmea_sentence else 'None'}, error: {str(e)}")
        return None
