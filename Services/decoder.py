import ais
import time

ais_buffer = {}  # Buffer untuk menyimpan fragment AIS
ais_buffer_time = {}


def try_decode(payload):
    """Coba decode dengan versi terbaik berdasarkan tipe pesan."""
    try:
        msg_type = int(payload[:6], 2)  # Ambil 6 bit pertama sebagai angka
    except ValueError:
        msg_type = 0  # Jika gagal deteksi, pakai versi default

    # Gunakan `version=2` dulu untuk pesan AIS tertentu
    if msg_type in {5, 19, 21, 24}:
        versions = [2, 0, 1]  # Coba 2 dulu, lalu 0, lalu 1
    else:
        versions = [0, 1, 2]  # Coba dari 0, lalu 1, lalu 2 untuk pesan lain

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
            fragment_count = int(parts[1])  # Total fragment
            fragment_number = int(parts[2])  # Nomor fragment saat ini
            message_id = parts[3]  # ID unik pesan multi-fragment
            channel = parts[4]  # A/B
            payload = parts[5]  # Gunakan payload asli tanpa modifikasi

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

            # Multi-fragment handling
            if unique_key not in ais_buffer:
                ais_buffer[unique_key] = [""] * fragment_count  # Buffer untuk semua fragment
                ais_buffer[unique_key + "_received"] = set()  # Simpan fragment yang sudah diterima
                ais_buffer_time[unique_key] = time.time()  # Simpan waktu saat fragment pertama diterima

            ais_buffer[unique_key][fragment_number - 1] = payload  # Simpan fragment ke posisi yang sesuai
            ais_buffer[unique_key + "_received"].add(fragment_number)  # Tandai fragment yang diterima

            # Jika semua fragment sudah terkumpul, gabungkan dan decode
            if len(ais_buffer[unique_key + "_received"]) == fragment_count:
                full_payload = "".join(ais_buffer.pop(unique_key))  # Gabungkan fragment
                ais_buffer.pop(unique_key  + "_received")  # Hapus record fragment yang diterima
                ais_buffer_time.pop(unique_key , None)  # Hapus timestamp buffer

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

            # **Tambahkan mekanisme timeout (5 detik)**
            if time.time() - ais_buffer_time.get(unique_key , 0) > 60:
                ais_buffer.pop(unique_key , None)
                ais_buffer.pop(unique_key  + "_received", None)
                ais_buffer_time.pop(unique_key , None)
                return None

            return None  # Fragment belum lengkap, tunggu dulu

        else:
            return None


    except Exception as e:
        return None
