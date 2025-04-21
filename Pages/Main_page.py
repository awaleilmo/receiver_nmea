import sys
import threading
from datetime import datetime

from PyQt6.QtCore import QThread, QTimer
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QIcon, QFont
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QSystemTrayIcon, QMenu, QLabel
from PyQt6.uic import loadUi

from Untils.logging_helper import error_file_logger
from Untils.path_helper import get_resource_path

from Services import sender, receiver
from Pages.Config_page import ConfigureWindow
from Pages.Connection_page import ConnectionWindow
from Services.SignalsMessages import signalsLogger, signalsError, signalsInfo
from Services.uploader import send_batch_data

from Workers.upload_worker import UploadWorker
from Workers.receiver_worker import ReceiverWorker
from Workers.sender_worker import SenderWorker


class AISViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        icon = QIcon(get_resource_path("Assets/logo_ipm.png"))
        self.setWindowIcon(icon)
        self.stop_receiver_event = threading.Event()
        self.stop_sender_event = threading.Event()
        self.stop_upload_event = threading.Event()
        self.max_log_lines = 50

        # Muat file .ui menggunakan loadUi dari PyQt6
        ui_path = get_resource_path("UI/main.ui")
        loadUi(ui_path, self)

        # System Tray
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(icon)
        self.tray_menu = QMenu()
        iconRunTray = QIcon.fromTheme("media-playback-start")
        iconStopTray = QIcon.fromTheme("media-playback-stop")
        self.open_app_action = self.tray_menu.addAction("Open App")
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
        self.open_app_action.triggered.connect(self.open_app_clicked)
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
        self.UploadLabel = QLabel("Upload: Stopped")
        self.statusbar.addPermanentWidget(self.ReceiverLabel)
        self.statusbar.addPermanentWidget(self.SenderLabel)
        self.statusbar.addPermanentWidget(self.UploadLabel)

        # Muat data awal
        self.labelInfo.setText("AIS Viewer")
        signalsLogger.new_data_received.connect(self.update_logger)
        signalsError.new_data_received.connect(self.update_error)
        signalsInfo.new_data_received.connect(self.update_info)
        self.start_upload()
        QTimer.singleShot(0, self.start_receiver)

        self.error_buffer = []
        self.error_timer = QTimer()
        self.error_timer.setInterval(1000)
        self.error_timer.timeout.connect(self.flush_error_buffer)
        self.error_timer.start()

    def update_logger(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"{timestamp} - {message}"
        self.plainTextLogger.appendPlainText(full_message)

        emoji_font = QFont("Noto Color Emoji")
        emoji_font.setPointSize(10)
        self.plainTextLogger.setFont(emoji_font)

        # Batasi jumlah baris
        if self.plainTextLogger.blockCount() > self.max_log_lines:
            # Ambil teks, hapus baris pertama
            current_text = self.plainTextLogger.toPlainText()
            new_text = '\n'.join(current_text.split('\n')[1:])
            self.plainTextLogger.setPlainText(new_text)

        # Scroll ke bawah
        self.plainTextLogger.verticalScrollBar().setValue(
            self.plainTextLogger.verticalScrollBar().maximum()
        )

    def update_error(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"{timestamp} - {message}"
        self.plainTextError.appendPlainText(full_message)

        emoji_font = QFont("Noto Color Emoji")
        emoji_font.setPointSize(10)
        self.plainTextError.setFont(emoji_font)

        # Batasi jumlah baris
        if self.plainTextError.blockCount() > self.max_log_lines:
            # Ambil teks, hapus baris pertama
            current_text = self.plainTextError.toPlainText()
            new_text = '\n'.join(current_text.split('\n')[1:])
            self.plainTextError.setPlainText(new_text)

        # Scroll ke bawah
        self.plainTextError.verticalScrollBar().setValue(
            self.plainTextError.verticalScrollBar().maximum()
        )

        self.error_buffer.append(message)

    def flush_error_buffer(self):
        for msg in self.error_buffer:
            error_file_logger.error(msg)
        self.error_buffer.clear()


    def update_info(self, message):
        self.labelInfo.setText(message)


    def start_upload(self):
        self.UploadLabel.setText("Upload: Running")
        self.upload_worker = UploadWorker(self.stop_upload_event)
        self.upload_worker.start()


    def stop_upload(self):
        self.UploadLabel.setText("Upload: Stopped")
        self.stop_upload_event.set()


    def start_receiver(self):
        if not hasattr(self, 'receiver_worker') or not self.receiver_worker.isRunning():
            self.stop_receiver_event.clear()
            self.receiver_worker = ReceiverWorker(self.stop_receiver_event)
            self.receiver_worker.start()
            self.actionRun_Receiver.setEnabled(False)
            self.actionStop_Receiver.setEnabled(True)
            self.run_receiver_action.setEnabled(False)
            self.stop_receiver_action.setEnabled(True)
            self.ReceiverLabel.setText("Receiver: Running")
            self.statusbar.showMessage('Receiver Started', 5000)


    def stop_receiver(self):
        if hasattr(self, 'receiver_worker') and self.receiver_worker and self.receiver_worker.isRunning():
            self.stop_receiver_event.set()
            self.receiver_worker.quit()
            self.receiver_worker.wait()
            self.receiver_worker = None
            self.actionRun_Receiver.setEnabled(True)
            self.actionStop_Receiver.setEnabled(False)
            self.run_receiver_action.setEnabled(True)
            self.stop_receiver_action.setEnabled(False)
            self.ReceiverLabel.setText("Receiver: Stopped")
            self.statusbar.showMessage('Receiver Stopped', 5000)


    def start_sender(self):
        if not hasattr(self, 'sender_worker') or not self.sender_worker.isRunning():
            self.stop_sender_event.clear()
            self.sender_worker = SenderWorker(self.stop_sender_event)
            self.sender_worker.start()
            self.actionRun_Sender_OpenCPN.setEnabled(False)
            self.actionStop_Sender_OpenCPN.setEnabled(True)
            self.run_sender_action.setEnabled(False)
            self.stop_sender_action.setEnabled(True)
            self.SenderLabel.setText("Sender: Running")
            self.statusbar.showMessage('Sender Started', 5000)

    def stop_sender(self):
        if hasattr(self, 'sender_worker') and self.sender_worker is not None:
            if self.sender_worker.isRunning():
                self.stop_sender_event.set()
                self.sender_worker.quit()
                self.sender_worker.wait()
            self.sender_worker = None
            self.actionRun_Sender_OpenCPN.setEnabled(True)
            self.actionStop_Sender_OpenCPN.setEnabled(False)
            self.run_sender_action.setEnabled(True)
            self.stop_sender_action.setEnabled(False)
            self.SenderLabel.setText("Sender: Stopped")
            self.statusbar.showMessage('Sender Stopped', 5000)


    def closeEvent(self, event):
        """Menangani event ketika jendela utama ditutup"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage("NMEA Receiver IPM", "Aplikasi masih berjalan di system tray.",
                                   QSystemTrayIcon.MessageIcon.Information)


    def tray_icon_clicked(self, reason):
        """Menampilkan jendela utama ketika ikon tray diklik"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show()
            self.raise_()
            self.activateWindow()


    def open_app_clicked(self):
        """Menampilkan jendela utama diklik"""
        self.show()
        self.raise_()
        self.activateWindow()


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
        self.stop_upload()
        dlg = ConfigureWindow(self)
        dlg.data_saved.connect(self.start_upload)
        dlg.exec()


    def showConnection(self):
        """Menampilkan jendela koneksi"""
        self.stop_receiver()
        dlg = ConnectionWindow(self)
        dlg.data_saved.connect(self.start_receiver)
        dlg.exec()
