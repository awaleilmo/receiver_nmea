import os
import sys
import shutil


def get_resource_path(relative_path, is_database=False):
    if is_database and relative_path.endswith('.db'):
        if sys.platform.startswith('win'):
            data_dir = os.path.join(os.environ['APPDATA'], 'SeaScope_Receiver')
        else:
            data_dir = os.path.join(os.path.expanduser('~'), '.SeaScope_Receiver')

        os.makedirs(data_dir, exist_ok=True)

        persistent_path = os.path.join(data_dir, relative_path)

        if hasattr(sys, '_MEIPASS') and not os.path.exists(persistent_path):
            bundled_db = os.path.join(sys._MEIPASS, relative_path)
            if os.path.exists(bundled_db):
                shutil.copy2(bundled_db, persistent_path)

        return persistent_path
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)