import threading
from datetime import datetime

from PyQt6.QtCore import Qt, QThread, QTimer, QSettings
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import (QApplication, QMainWindow, QSystemTrayIcon, QMenu, QLabel,
                             QHBoxLayout, QVBoxLayout, QWidget, QFrame, QProgressDialog, QProgressBar, QDialog)
from PyQt6.uic import loadUi

from Pages.Config_page import ConfigureWindow
from Pages.Connection_page import ConnectionWindow
from Services.SignalsMessages import signalsLogger, signalsError, signalsInfo, signalsWarning
from Untils.path_helper import get_resource_path
from Untils.logging_helper import error_file_logger

from Workers.receiver_worker import ReceiverWorker
from Workers.sender_worker import SenderWorker
from Workers.upload_worker import UploadWorker
from Workers.worker_manager import WorkerManager


class AISViewer(QMainWindow):
    MAX_LOG_ITEMS = 1000
    STATUS_MESSAGE_TIMEOUT = 5000

    def __init__(self):
        super().__init__()
        self.worker_manager = WorkerManager()
        self.worker_manager.status_changed.connect(self._handle_worker_status)
        self.setup_base_ui()
        self.setup_thread_management()
        self.setup_system_tray()
        self.setup_signals()
        self.setup_status_bar()
        self.setup_error_logging()
        self.start_upload()
        self.restore_window_state()

    def _handle_worker_status(self, worker_type, status):
        label = getattr(self, f"{worker_type.capitalize()}Label", None)
        if not label: return

        label.setText(f"{worker_type.capitalize()}: {status.capitalize()}")
        style = "color: green; font-weight: bold;" if status == 'running' else ""
        label.setStyleSheet(style)

    def setup_base_ui(self):
        self.app_icon = QIcon(get_resource_path("Assets/logo_ipm.png"))
        self.setWindowIcon(self.app_icon)
        self.setMinimumSize(800, 600)
        ui_path = get_resource_path("UI/main.ui")
        loadUi(ui_path, self)
        self.labelInfo.setText("AIS Viewer")
        QTimer.singleShot(0, self.start_receiver)

    def setup_thread_management(self):
        self.receiver_worker = None
        self.sender_worker = None
        self.upload_worker = None

        self.stop_receiver_event = threading.Event()
        self.stop_sender_event = threading.Event()
        self.stop_upload_event = threading.Event()

    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.app_icon)
        self.tray_menu = QMenu()

        iconRunTray = QIcon.fromTheme("media-playback-start")
        iconStopTray = QIcon.fromTheme("media-playback-stop")

        self.open_app_action = self.tray_menu.addAction("Open App")
        self.run_receiver_action = self.tray_menu.addAction("Run Receiver")
        self.stop_receiver_action = self.tray_menu.addAction("Stop Receiver")
        self.run_sender_action = self.tray_menu.addAction("Run Sender")
        self.stop_sender_action = self.tray_menu.addAction("Stop Sender")
        self.exit_action = self.tray_menu.addAction("Exit")

        self.run_receiver_action.setIcon(iconRunTray)
        self.stop_receiver_action.setIcon(iconStopTray)
        self.run_sender_action.setIcon(iconRunTray)
        self.stop_sender_action.setIcon(iconStopTray)

        self.run_receiver_action.setEnabled(True)
        self.stop_receiver_action.setEnabled(False)
        self.run_sender_action.setEnabled(True)
        self.stop_sender_action.setEnabled(False)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()

    def setup_signals(self):
        self.tray_icon.activated.connect(self.tray_icon_clicked)
        self.open_app_action.triggered.connect(self.open_app_clicked)
        self.run_receiver_action.triggered.connect(self.start_receiver)
        self.stop_receiver_action.triggered.connect(self.stop_receiver)
        self.run_sender_action.triggered.connect(self.start_sender)
        self.stop_sender_action.triggered.connect(self.stop_sender)
        self.exit_action.triggered.connect(self.exit)

        self.actionExit.triggered.connect(self.exit)
        self.actionConfigure.triggered.connect(self.showConfigure)
        self.actionConnections.triggered.connect(self.showConnection)
        self.actionRun_Receiver.triggered.connect(self.start_receiver)
        self.actionStop_Receiver.triggered.connect(self.stop_receiver)
        self.actionRun_Sender_OpenCPN.triggered.connect(self.start_sender)
        self.actionStop_Sender_OpenCPN.triggered.connect(self.stop_sender)

        # Logger signals
        signalsLogger.new_data_received.connect(self.update_logger)
        signalsError.new_data_received.connect(self.update_error)
        signalsInfo.new_data_received.connect(self.update_info)
        signalsWarning.new_data_received.connect(self.update_warning)

    def setup_status_bar(self):
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(5)

        self.ReceiverLabel = QLabel("Receiver: Stopped")
        self.SenderLabel = QLabel("Sender: Stopped")
        self.UploadLabel = QLabel("Upload: Stopped")

        for label in [self.ReceiverLabel, self.SenderLabel, self.UploadLabel]:
            label.setMinimumWidth(150)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFrameShape(QFrame.Shape.Panel)
            label.setFrameShadow(QFrame.Shadow.Sunken)

        status_layout.addWidget(self.ReceiverLabel)
        status_layout.addWidget(self.SenderLabel)
        status_layout.addWidget(self.UploadLabel)
        status_layout.addStretch(1)

        self.statusbar.addPermanentWidget(status_widget, 0)

    def setup_error_logging(self):
        self.error_buffer = []
        self.error_timer = QTimer()
        self.error_timer.setInterval(1000)
        self.error_timer.timeout.connect(self.flush_error_buffer)
        self.error_timer.start()

    def flush_error_buffer(self):
        for msg in self.error_buffer:
            error_file_logger.error(msg)
        self.error_buffer.clear()

    def restore_window_state(self):
        settings = QSettings("IPM", "SeaScope_Receiver")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1000, 700)

    def save_window_state(self):
        settings = QSettings("IPM", "SeaScope_Receiver")
        settings.setValue("geometry", self.saveGeometry())

    def update_logger(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"{timestamp} - {message}"

        emoji_font = QFont("Noto Color Emoji")
        emoji_font.setPointSize(10)
        self.plainTextLogger.setFont(emoji_font)

        self.plainTextLogger.appendPlainText(full_message)

        # Limit untuk tidak terlalu banyak
        if self.plainTextLogger.blockCount() > self.MAX_LOG_ITEMS:
            current_text = self.plainTextLogger.toPlainText()
            new_text = '\n'.join(current_text.split('\n')[1:])
            self.plainTextLogger.setPlainText(new_text)

        self.plainTextLogger.verticalScrollBar().setValue(
            self.plainTextLogger.verticalScrollBar().maximum()
        )

    def update_error(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_message = f"{timestamp} - 🚨 ERROR: {message}"

        # Set emoji font
        emoji_font = QFont("Noto Color Emoji")
        emoji_font.setPointSize(10)
        self.plainTextError.setFont(emoji_font)
        self.plainTextError.appendPlainText(error_message)
        self.error_buffer.append(message)
        if self.plainTextError.blockCount() > self.MAX_LOG_ITEMS:
            current_text = self.plainTextError.toPlainText()
            new_text = '\n'.join(current_text.split('\n')[1:])
            self.plainTextError.setPlainText(new_text)
        self.plainTextError.verticalScrollBar().setValue(
            self.plainTextError.verticalScrollBar().maximum()
        )

    def update_info(self, message):
        self.update_logger(f"ℹ️ INFO: {message}")
        self.labelInfo.setText(message)

    def update_warning(self, message):
        self.update_logger(f"⚠️ WARNING: {message}")

    def create_progress_dialog(self, message):
        dialog = QDialog(self)
        dialog.setWindowTitle("Please Wait")
        dialog.setModal(True)
        dialog.setFixedSize(250, 180)
        dialog.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        svg = QSvgWidget(get_resource_path("Assets/loading.svg"))
        svg.setFixedSize(64, 64)
        layout.addWidget(svg, alignment=Qt.AlignmentFlag.AlignCenter)

        timer = QTimer(dialog)
        timer.timeout.connect(lambda: None)  # Force UI update
        timer.start(100)

        return dialog

    def start_upload(self):
        self.stop_upload_event.clear()
        self.upload_worker = UploadWorker(self.stop_upload_event)
        self.upload_worker.start()
        self.UploadLabel.setText("Upload: Running")
        self.UploadLabel.setStyleSheet("QLabel { color: green; font-weight: bold; }")
        self.statusbar.showMessage('Upload Service Started', self.STATUS_MESSAGE_TIMEOUT)

    def stop_upload(self):
        if hasattr(self, 'upload_worker') and self.upload_worker and self.upload_worker.isRunning():
            self.stop_upload_event.set()
            self.upload_worker.quit()
            self.upload_worker.wait()
            self.upload_worker = None
            self.UploadLabel.setText("Upload: Stopped")
            self.UploadLabel.setStyleSheet("")
            self.statusbar.showMessage('Upload Service Stopped', self.STATUS_MESSAGE_TIMEOUT)

    def start_receiver(self):
        # if not hasattr(self, 'receiver_worker') or not self.receiver_worker or not self.receiver_worker.isRunning():
        progress_dialog = self.create_progress_dialog("Starting receiver service...")
        progress_dialog.show()

        # self.stop_receiver_event.clear()
        # self.receiver_worker = ReceiverWorker(self.stop_receiver_event)
        # self.receiver_worker.start()
        self.worker_manager.start_worker('receiver', ReceiverWorker)

        self.actionRun_Receiver.setEnabled(False)
        self.actionStop_Receiver.setEnabled(True)
        self.run_receiver_action.setEnabled(False)
        self.stop_receiver_action.setEnabled(True)
        # self.ReceiverLabel.setText("Receiver: Running")
        # self.ReceiverLabel.setStyleSheet("QLabel { color: green; font-weight: bold; }")

        QTimer.singleShot(1000, progress_dialog.close)
        self.statusbar.showMessage('Receiver Started', self.STATUS_MESSAGE_TIMEOUT)

    def stop_receiver(self):
        # if hasattr(self, 'receiver_worker') and self.receiver_worker and self.receiver_worker.isRunning():
        progress_dialog = self.create_progress_dialog("Stopping receiver service...")
        progress_dialog.show()

        # self.stop_receiver_event.set()
        # self.receiver_worker.quit()
        # self.receiver_worker.wait()
        # self.receiver_worker = None
        self.worker_manager.stop_worker('receiver')

        self.actionRun_Receiver.setEnabled(True)
        self.actionStop_Receiver.setEnabled(False)
        self.run_receiver_action.setEnabled(True)
        self.stop_receiver_action.setEnabled(False)

        # self.ReceiverLabel.setText("Receiver: Stopped")
        # self.ReceiverLabel.setStyleSheet("")

        QTimer.singleShot(1000, progress_dialog.close)
        self.statusbar.showMessage('Receiver Stopped', self.STATUS_MESSAGE_TIMEOUT)

    def start_sender(self):
        if not hasattr(self, 'sender_worker') or not self.sender_worker or not self.sender_worker.isRunning():
            progress_dialog = self.create_progress_dialog("Starting sender service...")
            progress_dialog.show()

            self.stop_sender_event.clear()
            self.sender_worker = SenderWorker(self.stop_sender_event)
            self.sender_worker.start()

            self.actionRun_Sender_OpenCPN.setEnabled(False)
            self.actionStop_Sender_OpenCPN.setEnabled(True)
            self.run_sender_action.setEnabled(False)
            self.stop_sender_action.setEnabled(True)

            self.SenderLabel.setText("Sender: Running")
            self.SenderLabel.setStyleSheet("QLabel { color: green; font-weight: bold; }")

            QTimer.singleShot(1000, progress_dialog.close)
            self.statusbar.showMessage('Sender Started', self.STATUS_MESSAGE_TIMEOUT)

    def stop_sender(self):
        if hasattr(self, 'sender_worker') and self.sender_worker and self.sender_worker.isRunning():
            progress_dialog = self.create_progress_dialog("Stopping sender service...")
            progress_dialog.show()

            self.stop_sender_event.set()
            self.sender_worker.quit()
            self.sender_worker.wait()
            self.sender_worker = None

            self.actionRun_Sender_OpenCPN.setEnabled(True)
            self.actionStop_Sender_OpenCPN.setEnabled(False)
            self.run_sender_action.setEnabled(True)
            self.stop_sender_action.setEnabled(False)

            self.SenderLabel.setText("Sender: Stopped")
            self.SenderLabel.setStyleSheet("")

            QTimer.singleShot(1000, progress_dialog.close)
            self.statusbar.showMessage('Sender Stopped', self.STATUS_MESSAGE_TIMEOUT)

    def closeEvent(self, event):
        self.save_window_state()
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "NMEA Receiver IPM",
            "Application is still running in system tray.",
            QSystemTrayIcon.MessageIcon.Information
        )

    def tray_icon_clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_main_window()

    def open_app_clicked(self):
        self.show_main_window()

    def show_main_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def exit(self):
        progress_dialog = self.create_progress_dialog("Quit...")
        progress_dialog.show()
        self.stop_upload()
        self.stop_receiver()
        self.stop_sender()
        self.save_window_state()
        if hasattr(self, 'error_timer') and self.error_timer.isActive():
            self.error_timer.stop()
        self.tray_icon.hide()
        QApplication.quit()

    def showConfigure(self):
        self.stop_receiver()
        QTimer.singleShot(500, self.stop_upload)
        QTimer.singleShot(700, lambda: self.showConfigureWindow())

    def showConfigureWindow(self):
        dlg = ConfigureWindow(self)
        dlg.data_saved.connect(self.start_upload)
        dlg.data_saved.connect(self.start_receiver)
        dlg.exec()

    def showConnection(self):
        self.stop_receiver()
        dlg = ConnectionWindow(self)
        dlg.data_saved.connect(self.start_receiver)
        dlg.exec()
