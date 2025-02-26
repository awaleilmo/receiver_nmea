import sqlite3
import sys
import threading
import webview
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableView, QPushButton, QLineEdit
from PyQt6.uic import loadUi
from PyQt6.QtCore import QFile, QThread, pyqtSignal

from config import DB_NAME, ALLOWED_MMSI
from constollers import get_all_ais_data
import receiver
import sender
from map_viewer import generate_map


class AISViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.toggleReceiver = False
        self.toggleSender = False
        self.stop_receiver_event = threading.Event()
        self.stop_sender_event = threading.Event()

        # Muat file .ui menggunakan loadUi dari PyQt6
        loadUi("main.ui", self)

        # Hubungkan tombol "Refresh Data" ke fungsi refresh_data
        self.btn_refresh.clicked.connect(self.load_data)

        # Hubungkan tombol "Set Filter" ke fungsi set_mmsi_filter
        self.btn_set_filter.clicked.connect(self.set_mmsi_filter)

        # Hubungkan tombol "Buka Peta" ke fungsi show_map
        self.btn_open_map.clicked.connect(self.show_map)

        # Gunakan satu fungsi untuk menangani start/stop
        self.btn_start_receiver.clicked.connect(self.toggle_receiver_function)
        self.btn_start_sender.clicked.connect(self.toggle_sender_function)

        # Hubungkan tombol "Exit" ke fungsi exit
        self.actionExit.triggered.connect(self.exit)

        # Status Threads
        self.receiver_thread = None
        self.sender_thread = None

        # Muat data awal
        self.load_data()

    def load_data(self):
        """Ambil data AIS terbaru dari database dan tampilkan di GUI"""
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(
            ["ID", "MMSI", "Latitude", "Longitude", "Speed (knots)", "Course (°)", "Ship Type", "Received At"]
        )

        rows = get_all_ais_data()

        # Tambahkan data ke model
        for row in rows:
            items = [
                QStandardItem(str(row["id"])),
                QStandardItem(str(row["mmsi"])),
                QStandardItem(str(row["lat"])),
                QStandardItem(str(row["lon"])),
                QStandardItem(str(row["sog"])),
                QStandardItem(str(row["cog"])),
                QStandardItem(str(row["ship_type"])),
                QStandardItem(str(row["received_at"]))
            ]

            self.model.appendRow(items)

        # Atur model ke QTableView
        self.tableView.setModel(self.model)

    def toggle_receiver_function(self):
        """Toggle fungsi start/stop receiver"""
        if not self.toggleReceiver:
            self.start_receiver()
        else:
            self.stop_receiver()

    def start_receiver(self):
        """Menjalankan penerima AIS di thread terpisah"""
        if self.receiver_thread is None or not self.receiver_thread.is_alive():
            self.stop_receiver_event.clear()
            self.btn_start_receiver.setText("Stop Receiver")
            self.receiver_thread = threading.Thread(target=self.run_receiver, daemon=True)
            self.receiver_thread.start()
            self.toggleReceiver = True
            print("Receiver Started")

    def run_receiver(self):
        """Fungsi wrapper untuk menjalankan receiver dengan event stop"""
        receiver.receive_nmea_udp(self.stop_receiver_event)

    def stop_receiver(self):
        """Menghentikan penerima AIS"""
        if self.receiver_thread and self.receiver_thread.is_alive():
            self.stop_receiver_event.set()  # Kirim sinyal untuk berhenti
            self.btn_start_receiver.setText("Start Receiver")
            self.toggleReceiver = False
            print("Receiver Stopped")

    def toggle_sender_function(self):
        """Toggle fungsi start/stop sender"""
        if not self.toggleSender:
            self.start_sender()
        else:
            self.stop_sender()

    def start_sender(self):
        """Menjalankan pengiriman AIS ke OpenCPN di thread terpisah"""
        if self.sender_thread is None or not self.sender_thread.is_alive():
            self.stop_sender_event.clear()
            self.btn_start_sender.setText("Stop Sender")
            self.sender_thread = threading.Thread(target=self.run_sender, daemon=True)
            self.sender_thread.start()
            self.toggleSender = True
            print("Sender Started")

    def run_sender(self):
        """Fungsi wrapper untuk menjalankan sender dengan event stop"""
        sender.send_ais_data(self.stop_sender_event)

    def stop_sender(self):
        """Menghentikan pengiriman AIS ke OpenCPN"""
        if self.sender_thread and self.sender_thread.is_alive():
            self.stop_sender_event.set()  # Kirim sinyal untuk berhenti
            self.btn_start_sender.setText("Start Sender")
            self.toggleSender = False
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
