import PyInstaller.__main__
import os
import sys
import platform as sys_platform
from shutil import which

APP_NAME = "SeaScope_Receiver"
MAIN_SCRIPT = "Main.py"
ICON_FILE = "Assets/logo_ipm.png"
ADDITIONAL_FILES = [
    "Assets/",
    "UI/",
    "Pages/",
    "Controllers/",
    "Models/",
    "Services/",
    "Workers/",
    "nmea_data.db",
    "requirements.txt"
]
OUTPUT_DIR = "dist"
VERSION = "1.0.0"


def check_dependencies():
    """Memeriksa dependensi yang diperlukan"""
    required = ['pyinstaller', 'PyQt6']
    missing = []

    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print("❌ Dependensi yang kurang:", ", ".join(missing))
        print("Instal dengan: pip install", " ".join(missing))
        sys.exit(1)

def get_target_platform():
    current_platform = sys_platform.system().lower()

    if current_platform in ['linux', 'windows']:
        print(f"\nDeteksi platform: {current_platform.capitalize()}")
        use_current = input(f"Gunakan {current_platform} sebagai target? (y/n): ").strip().lower()
        if use_current == 'y':
            return current_platform

    print("\nPilih platform target build:")
    print("1. Windows")
    print("2. Linux")
    choice = input("Masukkan pilihan (1/2): ").strip()
    while choice not in ['1', '2']:
        print("Pilihan tidak valid!")
        choice = input("Masukkan pilihan (1/2): ").strip()
    return 'windows' if choice == '1' else 'linux'

def get_icon_path(platform):
    icons = {
        'windows': ["Assets/logo_ipm.ico"],
        'linux': ["Assets/logo_ipm.png"]
    }

    for icon in icons.get(platform, []):
        if os.path.exists(icon):
            return icon
    return None

def get_additional_data(platform):
    data = []
    separator = ';' if platform == 'windows' else ':'

    for item in ADDITIONAL_FILES:
        if item.endswith('/'):
            folder = item[:-1]
            if not os.path.exists(folder):
                continue

            for root, _, files in os.walk(folder):
                for file in files:
                    if file.endswith('.pyc') or file.startswith('.'):
                        continue

                    src = os.path.join(root, file)
                    relative = os.path.relpath(src, ".")
                    dest = os.path.dirname(relative)
                    entry = f"{src}{separator}{dest if dest else '.'}"
                    print(f"📦 Menambahkan file: {entry}")
                    data.append(entry)
        else:
            if os.path.exists(item):
                entry = f"{item}{separator}."
                print(f"📦 Menambahkan file: {entry}")
                data.append(entry)
    return data

def build_app():
    platform = get_target_platform()
    is_windows = platform == 'windows'

    icon_file = get_icon_path(platform)
    if not icon_file:
        print("⚠️ Peringatan: File icon tidak ditemukan")

    pyinstaller_args = [
        "--onefile",
        "--windowed" if is_windows else "--noconsole",
        f"--name={APP_NAME}",
        f"--distpath={OUTPUT_DIR}",
        f"--workpath=build_{platform}",
        "--add-data=migrations.py;." if is_windows else "--add-data=migrations.py:.",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PyQt6.uic",
        "--hidden-import=sqlalchemy",
        "--hidden-import=logging",
        "--hidden-import=datetime"
    ]

    # if os.path.exists("Pages"):
    #     pyinstaller_args.append("--hidden-import=Pages")

    if icon_file:
        pyinstaller_args.append(f"--icon={icon_file}")

    # Tambahkan data tambahan
    additional_data = get_additional_data(platform)
    pyinstaller_args.extend([f"--add-data={item}" for item in additional_data])

    # Tambahan khusus Linux
    if platform == 'linux':
        pyinstaller_args.extend([
            "--hidden-import=xcbgen",
            "--hidden-import=dbus",
            "--hidden-import=gi"
        ])

        # Cek apakah ada Qt5/Qt6 yang terinstall
        if which('qmake-qt6'):
            pyinstaller_args.append("--qt-version=6")
        elif which('qmake-qt5'):
            pyinstaller_args.append("--qt-version=5")

    # Build final
    print(f"\n🔧 Membangun untuk {platform.capitalize()}...")
    print("Perintah PyInstaller:")
    print(" ".join(pyinstaller_args + [MAIN_SCRIPT]))

    try:
        PyInstaller.__main__.run(pyinstaller_args + [MAIN_SCRIPT])
        print(f"\n✅ Build selesai! File ada di: {OUTPUT_DIR}/{APP_NAME}{'.exe' if is_windows else ''}")
    except Exception as e:
        print(f"\n❌ Build gagal: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print(f"🛠️ Builder untuk {APP_NAME} v{VERSION}")
    build_app()
