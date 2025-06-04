import ais
import time
import json
import re

from Untils.logging_helper import sys_logger

ais_buffer = {}
ais_buffer_time = {}


def try_decode(payload):
    """Coba decode dengan versi terbaik berdasarkan tipe pesan."""
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
                return decoded_messages[0], version  # Ambil pesan pertama jika list
            return decoded_messages, version  # Jika bukan list, gunakan apa adanya
        except Exception as e:
            continue
    return None, None  # Jika semua gagal, kembalikan None

def decode_ais(nmea_sentence):
    """Gabungkan multi-fragment AIS sebelum decoding."""
    try:
        parts = nmea_sentence.split(",")

        if len(parts) > 5:
            fragment_count = int(parts[1])
            fragment_number = int(parts[2])
            message_id = parts[3]
            channel = parts[4]
            payload = parts[5]

            unique_key = f"{message_id}_{channel}"

            if fragment_count == 1:
                decoded_data, version = try_decode(payload)
                if not decoded_data:
                    return None

                if isinstance(decoded_data, dict):
                    decoded_data["channel"] = channel
                    decoded_data["message_id"] = message_id
                    decoded_data["fragment_count"] = fragment_count

                return decoded_data

            if unique_key not in ais_buffer:
                ais_buffer[unique_key] = [""] * fragment_count
                ais_buffer[unique_key + "_received"] = set()
                ais_buffer_time[unique_key] = time.time()

            ais_buffer[unique_key][fragment_number - 1] = payload
            ais_buffer[unique_key + "_received"].add(fragment_number)

            if len(ais_buffer[unique_key + "_received"]) == fragment_count:
                full_payload = "".join(ais_buffer.pop(unique_key))
                ais_buffer.pop(unique_key + "_received")
                ais_buffer_time.pop(unique_key, None)

                try:
                    decoded_data, version = try_decode(full_payload)

                    if not decoded_data:
                        return None

                    if isinstance(decoded_data, dict):
                        decoded_data["channel"] = channel
                        decoded_data["message_id"] = message_id
                        decoded_data["fragment_count"] = fragment_count

                    return decoded_data

                except Exception as e:
                    return None

            if time.time() - ais_buffer_time.get(unique_key, 0) > 60:
                ais_buffer.pop(unique_key, None)
                ais_buffer.pop(unique_key + "_received", None)
                ais_buffer_time.pop(unique_key, None)
                return None

            return None

        else:
            return None


    except Exception as e:
        sys_logger.error(f"Failed to decode: {nmea_sentence}, error: {str(e)}")
        return None
