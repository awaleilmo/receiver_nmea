import os
import sys
import shutil


def get_resource_path(relative_path, is_database=False, is_config=False):
    """
    Get the correct path for resources, databases, and config files
    """

    if is_config and relative_path.endswith('.ini'):
        # Untuk config file, prioritaskan file di direktori executable/current directory
        try:
            if hasattr(sys, '_MEIPASS'):
                # Running as compiled executable
                exe_dir = os.path.dirname(sys.executable)
                external_config = os.path.join(exe_dir, relative_path)

                # Jika ada config eksternal, gunakan itu
                if os.path.exists(external_config):
                    return external_config

                # Jika tidak ada, copy dari bundle ke direktori executable
                bundled_config = os.path.join(sys._MEIPASS, relative_path)
                if os.path.exists(bundled_config) and not os.path.exists(external_config):
                    shutil.copy2(bundled_config, external_config)
                    return external_config

                return external_config
            else:
                # Development mode - gunakan file lokal
                return os.path.join(os.path.abspath("."), relative_path)
        except Exception as e:
            print(f"Error handling config path: {str(e)}")
            return os.path.join(os.path.abspath("."), relative_path)

    if is_database and relative_path.endswith('.db'):
        # Untuk database, tetap simpan di direktori executable/user data
        try:
            if hasattr(sys, '_MEIPASS'):
                exe_dir = os.path.dirname(sys.executable)
            else:
                exe_dir = os.path.abspath(".")

            os.makedirs(exe_dir, exist_ok=True)
            return os.path.join(exe_dir, relative_path)
        except Exception as e:
            print(f"Error setting database path: {str(e)}")
            return os.path.join(os.path.abspath("."), relative_path)

    # Untuk resource lainnya (UI, Assets, dll)
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)