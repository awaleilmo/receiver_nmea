import sys
import threading
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QSystemTrayIcon, QMenu, QLabel
from PyQt6.uic import loadUi


# from Controllers.AISHistory_controller import get_all_ais_data
from Services import sender, receiver
from Pages.Config_page import ConfigureWindow
from Pages.Connection_page import ConnectionWindow


# from map_viewer import generate_map


class AISViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        icon = QIcon("Assets/logo_ipm.png")
        self.setWindowIcon(icon)
        self.receiver_threads = []
        self.toggleReceiver = False
        self.toggleSender = False
        self.stop_receiver_event = threading.Event()
        self.stop_sender_event = threading.Event()

        # Muat file .ui menggunakan loadUi dari PyQt6
        loadUi("UI/main.ui", self)

        # System Tray
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(icon)
        self.tray_menu = QMenu()
        iconRunTray = QIcon.fromTheme("media-playback-start")
        iconStopTray = QIcon.fromTheme("media-playback-stop")
        self.run_receiver_action = self.tray_menu.addAction("Run Receiver")
        self.stop_receiver_action = self.tray_menu.addAction("Stop Receiver")
        self.run_sender_action = self.tray_menu.addAction("Run Sender")
        self.stop_sender_action = self.tray_menu.addAction("Stop Sender")
        self.exit_action = self.tray_menu.addAction("Exit")
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()

        self.run_receiver_action.setEnabled(True)
        self.stop_receiver_action.setEnabled(False)

        self.run_sender_action.setEnabled(True)
        self.stop_sender_action.setEnabled(False)

        self.run_receiver_action.setIcon(iconRunTray)
        self.stop_receiver_action.setIcon(iconStopTray)

        self.run_sender_action.setIcon(iconRunTray)
        self.stop_sender_action.setIcon(iconStopTray)

        # Hubungkan tindakan tray
        self.tray_icon.activated.connect(self.tray_icon_clicked)
        self.run_receiver_action.triggered.connect(self.start_receiver)
        self.stop_receiver_action.triggered.connect(self.stop_receiver)
        self.run_sender_action.triggered.connect(self.start_sender)
        self.stop_sender_action.triggered.connect(self.stop_sender)
        self.exit_action.triggered.connect(self.exit)

        # Hubungkan tombol "Refresh Data" ke fungsi refresh_data
        self.btn_refresh.clicked.connect(self.load_data)

        # Hubungkan tombol "Set Filter" ke fungsi set_mmsi_filter
        # self.btn_set_filter.clicked.connect(self.set_mmsi_filter)

        # Hubungkan tombol "Buka Peta" ke fungsi show_map
        self.btn_open_map.clicked.connect(self.show_map)

        # Hubungkan tombol "Exit" ke fungsi exit
        self.actionExit.triggered.connect(self.exit)
        self.actionConfigure.triggered.connect(self.showConfigure)
        self.actionConnections.triggered.connect(self.showConnection)
        self.actionRun_Receiver.triggered.connect(self.start_receiver)
        self.actionStop_Receiver.triggered.connect(self.stop_receiver)
        self.actionRun_Sender_OpenCPN.triggered.connect(self.start_sender)
        self.actionStop_Sender_OpenCPN.triggered.connect(self.stop_sender)

        # Status Threads
        self.receiver_thread = None
        self.sender_thread = None

        self.ReceiverLabel = QLabel("Receiver: Stopped")
        self.SenderLabel = QLabel("Sender: Stopped")
        self.statusbar.addPermanentWidget(self.ReceiverLabel)
        self.statusbar.addPermanentWidget(self.SenderLabel)

        # Muat data awal
        self.load_data()

    def load_data(self):
        """Ambil data AIS terbaru dari database dan tampilkan di GUI"""
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(
            ["ID", "MMSI", "Latitude", "Longitude", "Speed (knots)", "Course (°)", "Ship Type", "Received At"]
        )

        # rows = get_all_ais_data()
        #
        # # Tambahkan data ke model
        # for row in rows:
        #     items = [
        #         QStandardItem(str(row["id"])),
        #         QStandardItem(str(row["mmsi"])),
        #         QStandardItem(str(row["lat"])),
        #         QStandardItem(str(row["lon"])),
        #         QStandardItem(str(row["sog"])),
        #         QStandardItem(str(row["cog"])),
        #         QStandardItem(str(row["ship_type"])),
        #         QStandardItem(str(row["received_at"]))
        #     ]
        #
        #     self.model.appendRow(items)

        # Atur model ke QTableView
        self.tableView.setModel(self.model)

    def run_receiver_thread(self):
        """Wrapper untuk menjalankan receiver di thread"""
        self.receiver_threads = receiver.start_multi_receiver(self.stop_receiver_event)

    def start_receiver(self):
        """Menjalankan penerima AIS di thread terpisah"""
        if not self.receiver_threads:
            self.stop_receiver_event.clear()
            self.stop_receiver_event = threading.Event()  # Buat stop event di awal
            receiver_thread = threading.Thread(target=self.run_receiver_thread, daemon=True)
            receiver_thread.start()
            self.actionRun_Receiver.setEnabled(False)
            self.actionStop_Receiver.setEnabled(True)
            self.run_receiver_action.setEnabled(False)
            self.stop_receiver_action.setEnabled(True)
            self.toggleReceiver = True
            self.ReceiverLabel.setText("Receiver: Running")
            self.statusbar.showMessage('Receiver Started', 5000)

    def stop_receiver(self):
        """Menghentikan penerima AIS"""
        if self.receiver_threads:
            self.stop_receiver_event.set()  # Kirim sinyal untuk berhenti
            for thread in self.receiver_threads:
                thread.join(timeout=5)  # Tunggu semua thread selesai

            self.receiver_threads = []  # Kosongkan daftar thread
            self.actionRun_Receiver.setEnabled(True)
            self.actionStop_Receiver.setEnabled(False)
            self.run_receiver_action.setEnabled(True)
            self.stop_receiver_action.setEnabled(False)
            self.toggleReceiver = False
            self.ReceiverLabel.setText("Receiver: Stopped")
            self.statusbar.showMessage('Receiver Stopped', 5000)

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
            self.sender_thread = threading.Thread(target=self.run_sender, daemon=True)
            self.sender_thread.start()
            self.actionRun_Sender_OpenCPN.setEnabled(False)
            self.actionStop_Sender_OpenCPN.setEnabled(True)
            self.run_sender_action.setEnabled(False)
            self.stop_sender_action.setEnabled(True)
            self.toggleSender = True
            self.SenderLabel.setText("Sender: Running")
            self.statusbar.showMessage('Sender Started', 5000)

    def run_sender(self):
        """Fungsi wrapper untuk menjalankan sender dengan event stop"""
        sender.send_ais_data(self.stop_sender_event)

    def stop_sender(self):
        """Menghentikan pengiriman AIS ke OpenCPN"""
        if self.sender_thread and self.sender_thread.is_alive():
            self.stop_sender_event.set()  # Kirim sinyal untuk berhenti
            self.actionRun_Sender_OpenCPN.setEnabled(True)
            self.actionStop_Sender_OpenCPN.setEnabled(False)
            self.run_sender_action.setEnabled(True)
            self.stop_sender_action.setEnabled(False)
            self.toggleSender = False
            self.SenderLabel.setText("Sender: Stopped")
            self.statusbar.showMessage('Sender Stopped', 5000)

    def show_map(self):
        """Menampilkan peta dengan lokasi kapal"""
        # map_path = generate_map()
        # webview.create_window("AIS Ship Tracker", map_path)
        # webview.start()

    # def set_mmsi_filter(self):
    #     """Memperbarui daftar MMSI yang akan dikirim ke OpenCPN"""
    #     global ALLOWED_MMSI
    #     filter_text = self.mmsi_entry.text().strip()
    #     mmsi_list = filter_text.split(",")
    #     ALLOWED_MMSI = [mmsi.strip() for mmsi in mmsi_list if mmsi.strip()]
    #     print(f"Filter MMSI diperbarui: {ALLOWED_MMSI}")

    def closeEvent(self, event):
        """Menangani event ketika jendela utama ditutup"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage("NMEA Receiver IPM", "Aplikasi masih berjalan di system tray.", QSystemTrayIcon.MessageIcon.Information)

    def tray_icon_clicked(self, reason):
        """Menampilkan jendela utama ketika ikon tray diklik"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show()

    def exit(self):
        """Menutup aplikasi sepenuhnya"""
        self.tray_icon.hide()
        QApplication.quit()

    def showConfigure(self):
        """Menampilkan jendela konfigurasi"""
        self.stop_receiver()
        dlg = ConfigureWindow(self)
        dlg.data_saved.connect(self.start_receiver())
        dlg.exec()

    def showConnection(self):
        """Menampilkan jendela koneksi"""
        self.stop_receiver()
        dlg = ConnectionWindow(self)
        # dlg.data_saved.connect(self.start_receiver())
        dlg.exec()