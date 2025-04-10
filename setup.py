import PyInstaller.__main__
import os

APP_NAME = "SeaScope_Receiver"
MAIN_SCRIPT = "Main.py"
ICON_FILE = "Assets/logo_ipm.ico"
ADDITIONAL_FILES = [
    "Assets/",
    "UI/",
    "nmea_data.db",
    "requirements.txt"
]
OUTPUT_DIR = "dist"
VERSION = "1.0.0"

def get_target_platform():
    print("\nPilih platform target build:")
    print("1. Windows")
    print("2. Linux")
    choice = input("Masukkan pilihan (1/2): ").strip()
    while choice not in ['1', '2']:
        print("Pilihan tidak valid!")
        choice = input("Masukkan pilihan (1/2): ").strip()
    return 'windows' if choice == '1' else 'linux'

def get_icon_path(platform):
    candidates = ["Assets/logo_ipm.ico", "Assets/logo_ipm.png"]
    for icon in candidates:
        if os.path.exists(icon):
            return icon
    return None

def get_additional_data(platform):
    data = []
    separator = ';' if platform == 'windows' else ':'

    for item in ADDITIONAL_FILES:
        if item.endswith('/'):
            folder = item[:-1]
            for root, _, files in os.walk(folder):
                for file in files:
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

    pyinstaller_args = [
        "--onefile",
        "--windowed" if is_windows else "--noconsole",
        f"--name={APP_NAME}",
        f"--distpath={OUTPUT_DIR}",
        f"--workpath=build_{platform}",
        "--add-data=migrations.py;." if is_windows else "--add-data=migrations.py:.",
        "--hidden-import=Controllers",
        "--hidden-import=Models",
        "--hidden-import=Services",
        "--hidden-import=Utils"
    ]

    if os.path.exists("Pages"):
        pyinstaller_args.append("--hidden-import=Pages")

    if icon_file:
        pyinstaller_args.append(f"--icon={icon_file}")

    # Tambahkan data tambahan
    pyinstaller_args.extend([f"--add-data={item}" for item in get_additional_data(platform)])

    # Build final
    print(f"\n🔧 Membangun untuk {platform.capitalize()}...")
    print("Perintah PyInstaller:")
    print(" ".join(pyinstaller_args + [MAIN_SCRIPT]))

    PyInstaller.__main__.run(pyinstaller_args + [MAIN_SCRIPT])

    print(f"\n✅ Build selesai! File ada di: {OUTPUT_DIR}/{APP_NAME}{'.exe' if is_windows else ''}")

if __name__ == "__main__":
    print(f"🛠️ Builder untuk {APP_NAME} v{VERSION}")
    build_app()
