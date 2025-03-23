import sys
import threading
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QSystemTrayIcon, QMenu, QLabel
from PyQt6.uic import loadUi


from Services import sender, receiver
from Pages.Config_page import ConfigureWindow
from Pages.Connection_page import ConnectionWindow
from Services.SignalsMessages import signals
from Services.uploader import send_batch_data

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
        self.stop_upload_event = threading.Event()

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
        self.list_model = QStandardItemModel(self)
        self.listView.setModel(self.list_model)
        signals.new_data_received.connect(self.update_log)
        self.start_upload()

    def update_log(self, message):
        item = QStandardItem(message)
        self.list_model.appendRow(item)

        # Auto-scroll ke item terbaru
        self.listView.scrollToBottom()

    def start_upload(self):
        upload_thread = threading.Thread(target=send_batch_data, args=(self.stop_upload_event,), daemon=True)
        upload_thread.start()

    def stop_upload(self):
        self.stop_upload_event.set()

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
        self.stop_upload()
        self.stop_receiver()
        self.stop_sender()
        self.tray_icon.hide()
        QApplication.quit()

    def showConfigure(self):
        """Menampilkan jendela konfigurasi"""
        self.stop_receiver()
        dlg = ConfigureWindow(self)
        # dlg.data_saved.connect(self.start_receiver())
        dlg.exec()

    def showConnection(self):
        """Menampilkan jendela koneksi"""
        self.stop_receiver()
        dlg = ConnectionWindow(self)
        # dlg.data_saved.connect(self.start_receiver())
        dlg.exec()