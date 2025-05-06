import os
import sys
import shutil


def get_resource_path(relative_path, is_database=False):
    if is_database and relative_path.endswith('.db'):
        #periksa jika berjalan untuk pyinstaller untuk executables jika tidak maka akan menggunakan path asli(current directory)
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

    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)