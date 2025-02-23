import sqlite3
import sys
import threading
import webview
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableView, QPushButton, QLineEdit
from PyQt6.uic import loadUi
from PyQt6.QtCore import QFile

from config import DB_NAME, ALLOWED_MMSI
from database import create_table
import receiver
import sender
from map_viewer import generate_map


class AISViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        # Muat file .ui menggunakan loadUi dari PyQt6
        loadUi("main.ui", self)

        # Hubungkan tombol "Refresh Data" ke fungsi refresh_data
        self.btn_refresh.clicked.connect(self.load_data)

        # Hubungkan tombol "Set Filter" ke fungsi set_mmsi_filter
        self.btn_set_filter.clicked.connect(self.set_mmsi_filter)

        # Hubungkan tombol "Buka Peta" ke fungsi show_map
        self.btn_open_map.clicked.connect(self.show_map)

        # Hubungkan tombol kontrol untuk Start/Stop Receiver
        self.btn_start_receiver.clicked.connect(self.start_receiver)
        self.btn_stop_receiver.clicked.connect(self.stop_receiver)

        # Hubungkan tombol kontrol untuk Start/Stop Sender
        self.btn_start_sender.clicked.connect(self.start_sender)
        self.btn_stop_sender.clicked.connect(self.stop_sender)

        # Hubungkan tombol "Exit" ke fungsi exit
        self.actionExit.triggered.connect(self.exit)

        # Status Threads
        self.receiver_thread = None
        self.sender_thread = None
        self.running_receiver = False
        self.running_sender = False

        # Inisialisasi database
        create_table()

        # Muat data awal
        self.load_data()

    def load_data(self):
        """Ambil data AIS terbaru dari database dan tampilkan di GUI"""
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(
            ["ID", "MMSI", "Latitude", "Longitude", "Speed (knots)", "Course (°)", "Ship Type", "Received At"]
        )

        connection = sqlite3.connect(DB_NAME)
        cursor = connection.cursor()
        cursor.execute(
            "SELECT id, mmsi, lat, lon, sog, cog, ship_type, received_at FROM ais_history ORDER BY id DESC LIMIT 20")
        rows = cursor.fetchall()
        connection.close()

        # Tambahkan data ke model
        for row in rows:
            items = [QStandardItem(str(item)) for item in row]
            self.model.appendRow(items)

        # Atur model ke QTableView
        self.tableView.setModel(self.model)

    def start_receiver(self):
        """Menjalankan penerima AIS di thread terpisah"""
        if not self.running_receiver:
            self.receiver_thread = threading.Thread(target=receiver.receive_nmea_udp, daemon=True)
            self.receiver_thread.start()
            self.running_receiver = True
            print("Receiver Started")

    def stop_receiver(self):
        """Menghentikan penerima AIS"""
        if self.running_receiver:
            receiver.stop_nmea_receiver()
            self.running_receiver = False
            print("Receiver Stopped")

    def start_sender(self):
        """Menjalankan pengiriman AIS ke OpenCPN di thread terpisah"""
        if not self.running_sender:
            self.sender_thread = threading.Thread(target=sender.send_ais_data, daemon=True)
            self.sender_thread.start()
            self.running_sender = True
            print("Sender Started")

    def stop_sender(self):
        """Menghentikan pengiriman AIS ke OpenCPN"""
        if self.running_sender:
            sender.stop_ais_sender()
            self.running_sender = False
            print("Sender Stopped")

    def show_map(self):
        """Menampilkan peta dengan lokasi kapal"""
        map_path = generate_map()
        webview.create_window("AIS Ship Tracker", map_path)
        webview.start()

    def set_mmsi_filter(self):
        """Memperbarui daftar MMSI yang akan dikirim ke OpenCPN"""
        global ALLOWED_MMSI
        filter_text = self.mmsi_entry.text().strip()
        mmsi_list = filter_text.split(",")
        ALLOWED_MMSI = [mmsi.strip() for mmsi in mmsi_list if mmsi.strip()]
        print(f"Filter MMSI diperbarui: {ALLOWED_MMSI}")

    def exit(self):
        """Menutup aplikasi"""
        sys.exit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AISViewer()
    window.show()
    sys.exit(app.exec())