import threading
from datetime import datetime

from PyQt6.QtCore import Qt, QThread, QTimer, QSettings
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import (QApplication, QMainWindow, QSystemTrayIcon, QMenu, QLabel,
                             QHBoxLayout, QVBoxLayout, QWidget, QFrame, QProgressDialog, QProgressBar, QDialog)
from PyQt6.uic import loadUi

from Controllers.Worker_controller import WorkerController
from Pages.Config_page import ConfigureWindow
from Pages.Connection_page import ConnectionWindow
from Services.SignalsMessages import signalsLogger, signalsError, signalsInfo, signalsWarning
from Services.log_manager import LogManager
from UI.components.main_window import BaseMainWindow
from UI.components.system_tray import SystemTrayManager
from Untils.path_helper import get_resource_path
from Pages.Log_page import LogViewerDialog

from Workers.receiver_worker import ReceiverWorker
from Workers.sender_worker import SenderWorker
from Workers.upload_worker import UploadWorker
from Workers.worker_manager import WorkerManager

from UI.components.progress_dialog import ProgressDialog


class AISViewer(BaseMainWindow):
    MAX_LOG_ITEMS = 1000
    STATUS_MESSAGE_TIMEOUT = 5000

    def __init__(self):
        super().__init__()
        self.worker_controller = WorkerController()
        self.log_manager = LogManager()

        self.tray_manager = SystemTrayManager(self.app_icon, self)

        self.progress_dialog = None

        self.setup_connections()
        self.setup_status_bar()
        self.setup_tray_connections()

        self.setup_signals()
        self.restore_window_state()
        self.startup()

    def setup_connections(self):
        self.worker_controller.status_changed.connect(self._handle_worker_status)

        self.log_manager.log_received.connect(self.update_logger)
        self.log_manager.info_received.connect(self.update_info)
        self.log_manager.warning_received.connect(self.update_warning)

    def startup(self):
        self._show_progress_dialog("Preparing to startup...")
        QTimer.singleShot(1000, lambda: [
            self.worker_controller.start_worker('receiver', ReceiverWorker),
            self.worker_controller.start_worker('upload', UploadWorker),
            self.actionRun_Uploader.setEnabled(False),
            self.actionStop_Uploader.setEnabled(True),
            self.actionRun_Receiver.setEnabled(False),
            self.actionStop_Receiver.setEnabled(True),
            self._close_progress()
        ])

    def _handle_worker_status(self, worker_type, status):

        label = getattr(self, f"{worker_type.capitalize()}Label", None)
        if not label:
            return

        label.setText(f"{worker_type.capitalize()}: {status.capitalize()}")
        style = "color: green; font-weight: bold;" if status == 'running' else ""
        label.setStyleSheet(style)

        # Update tray actions state
        states = {
            'run_receiver': status != 'running',
            'stop_receiver': status == 'running',
            'run_sender': status != 'running',
            'stop_sender': status == 'running',
            'run_upload': status != 'running',
            'stop_upload': status == 'running',
        }
        self.tray_manager.set_actions_state(**states)

    def _show_progress_dialog(self, message):
        if self.progress_dialog:
            self.progress_dialog.close()

        self.progress_dialog = ProgressDialog(self, message)
        self.progress_dialog.show()

    def _close_progress(self):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog.deleteLater()
            self.progress_dialog = None

    def setup_tray_connections(self):
        # Koneksi untuk show/hide
        self.tray_manager.open_app_requested.connect(self.show_main_window)
        self.tray_manager.exit_requested.connect(self.exit)

        # Koneksi untuk worker control
        self.tray_manager.run_receiver_requested.connect(self.start_receiver)
        self.tray_manager.stop_receiver_requested.connect(self.stop_receiver)
        self.tray_manager.run_sender_requested.connect(self.start_sender)
        self.tray_manager.stop_sender_requested.connect(self.stop_sender)
        self.tray_manager.run_upload_requested.connect(self.start_upload)
        self.tray_manager.stop_upload_requested.connect(self.stop_upload)

    def setup_signals(self):

        self.actionExit.triggered.connect(self.exit)
        self.actionLogs.triggered.connect(self.show_log_viewer)
        self.actionConfigure.triggered.connect(self.showConfigure)
        self.actionConnections.triggered.connect(self.showConnection)
        self.actionRun_Receiver.triggered.connect(self.start_receiver)
        self.actionStop_Receiver.triggered.connect(self.stop_receiver)
        self.actionRun_Sender_OpenCPN.triggered.connect(self.start_sender)
        self.actionStop_Sender_OpenCPN.triggered.connect(self.stop_sender)
        self.actionRun_Uploader.triggered.connect(self.start_upload)
        self.actionStop_Uploader.triggered.connect(self.stop_upload)

        # Logger signals
        signalsLogger.new_data_received.connect(self.update_logger)
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

    def update_info(self, message):
        self.labelInfo.setText(message)
        self.labelInfo.setToolTip(message)
        QTimer.singleShot(5000, lambda: [
            self.labelInfo.setText("AIS Viewer"),
            self.labelInfo.setToolTip("AIS Viewer")
        ])

    def update_warning(self, message):
        self.update_logger(f"⚠️ WARNING: {message}")

    def start_upload(self):
        self._show_progress_dialog("Starting uploader service...")
        self.worker_controller.start_worker('upload', UploadWorker)

        self.actionRun_Uploader.setEnabled(False)
        self.actionStop_Uploader.setEnabled(True)

        QTimer.singleShot(200, self._close_progress)
        self.statusbar.showMessage('Upload Service Started', self.STATUS_MESSAGE_TIMEOUT)

    def stop_upload(self):
        self._show_progress_dialog("Starting uploader service...")

        self.worker_controller.stop_worker('upload')

        self.actionRun_Uploader.setEnabled(True)
        self.actionStop_Uploader.setEnabled(False)

        QTimer.singleShot(200, self._close_progress)
        self.statusbar.showMessage('Upload Service Stopped', self.STATUS_MESSAGE_TIMEOUT)

    def start_receiver(self):
        self._show_progress_dialog("Starting receiver service...")

        self.worker_controller.start_worker('receiver', ReceiverWorker)

        self.actionRun_Receiver.setEnabled(False)
        self.actionStop_Receiver.setEnabled(True)

        QTimer.singleShot(200, self._close_progress)
        self.statusbar.showMessage('Receiver Started', self.STATUS_MESSAGE_TIMEOUT)

    def stop_receiver(self):
        self._show_progress_dialog("Stopping receiver service...")

        self.worker_controller.stop_worker('receiver')

        self.actionRun_Receiver.setEnabled(True)
        self.actionStop_Receiver.setEnabled(False)

        QTimer.singleShot(200, self._close_progress)
        self.statusbar.showMessage('Receiver Stopped', self.STATUS_MESSAGE_TIMEOUT)

    def start_sender(self):
        self._show_progress_dialog("Starting sender service...")

        self.worker_controller.start_worker('sender', SenderWorker)

        self.actionRun_Sender_OpenCPN.setEnabled(False)
        self.actionStop_Sender_OpenCPN.setEnabled(True)

        QTimer.singleShot(200, self._close_progress)
        self.statusbar.showMessage('Sender Started', self.STATUS_MESSAGE_TIMEOUT)

    def stop_sender(self):
        self._show_progress_dialog("Stopping sender service...")

        self.worker_controller.stop_worker('sender')

        self.actionRun_Sender_OpenCPN.setEnabled(True)
        self.actionStop_Sender_OpenCPN.setEnabled(False)

        QTimer.singleShot(200, self._close_progress)
        self.statusbar.showMessage('Sender Stopped', self.STATUS_MESSAGE_TIMEOUT)

    def closeEvent(self, event):
        self.save_window_state()
        event.ignore()
        self.hide()
        self.tray_manager.show()
        self.tray_manager.show_message(
            "NMEA Receiver IPM",
            "Application is still running in system tray.",
            # QSystemTrayIcon.MessageIcon.Information
        )

    def show_main_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def open_app_clicked(self):
        self.show_main_window()

    def exit(self):
        self._show_progress_dialog("Quit...")
        if hasattr(self, 'error_timer') and self.error_timer.isActive():
            self.error_timer.stop()
        self.tray_manager.hide()
        self._close_progress()
        QApplication.quit()

    def showConfigure(self):
        self._show_progress_dialog("Preparing to configure...")

        self.worker_controller.stop_worker('receiver')
        self.worker_controller.stop_worker('sender')
        self.worker_controller.stop_worker('upload')
        self.actionRun_Receiver.setEnabled(True)
        self.actionStop_Receiver.setEnabled(False)
        self.actionRun_Uploader.setEnabled(True)
        self.actionStop_Uploader.setEnabled(False)
        self.actionRun_Sender_OpenCPN.setEnabled(True)
        self.actionStop_Sender_OpenCPN.setEnabled(False)
        QTimer.singleShot(200, lambda: [
            self._close_progress(),
            self._open_config_window()
        ])

    def _open_config_window(self):
        dlg = ConfigureWindow(self)
        dlg.data_saved.connect(lambda: [
            self.worker_controller.start_worker('receiver', ReceiverWorker),
            self.worker_controller.start_worker('upload', UploadWorker),
            self.worker_controller.start_worker('sender', SenderWorker),
            self.actionRun_Receiver.setEnabled(False),
            self.actionStop_Receiver.setEnabled(True),
            self.actionRun_Uploader.setEnabled(False),
            self.actionStop_Uploader.setEnabled(True),
            self.actionRun_Sender_OpenCPN.setEnabled(False),
            self.actionStop_Sender_OpenCPN.setEnabled(True)
        ])
        dlg.exec()

    def showConnection(self):
        self._show_progress_dialog("Preparing to connection...")

        def stop_callback():
            self._close_progress()
            self._show_connection_window()

        self.actionRun_Receiver.setEnabled(True)
        self.actionStop_Receiver.setEnabled(False)
        self.worker_controller.stop_worker('receiver', stop_callback)

    def _show_connection_window(self):
        dlg = ConnectionWindow(self)
        dlg.data_saved.connect(lambda: [
            self.worker_controller.start_worker('receiver', ReceiverWorker),
            self.actionRun_Receiver.setEnabled(False),
            self.actionStop_Receiver.setEnabled(True)
        ])
        dlg.exec()

    def show_log_viewer(self):
        dlg = LogViewerDialog(self)
        dlg.exec()