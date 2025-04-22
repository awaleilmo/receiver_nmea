import threading
from datetime import datetime

from PyQt6.QtCore import Qt, QThread, QTimer, QSettings
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtWidgets import (QApplication, QMainWindow, QSystemTrayIcon, QMenu, QLabel,
                             QHBoxLayout, QWidget, QFrame, QProgressDialog, QProgressBar)
from PyQt6.uic import loadUi
from PySide6.QtWidgets import QPushButton

from Pages.Config_page import ConfigureWindow
from Pages.Connection_page import ConnectionWindow
from Services.SignalsMessages import signalsLogger, signalsError, signalsInfo, signalsWarning
from Untils.path_helper import get_resource_path
from Untils.logging_helper import error_file_logger

from Workers.receiver_worker import ReceiverWorker
from Workers.sender_worker import SenderWorker
from Workers.upload_worker import UploadWorker


class AISViewer(QMainWindow):
    MAX_LOG_ITEMS = 1000
    STATUS_MESSAGE_TIMEOUT = 5000

    def __init__(self):
        super().__init__()
        self.setup_base_ui()
        self.setup_thread_management()
        self.setup_system_tray()
        self.setup_signals()
        self.setup_status_bar()
        self.setup_error_logging()
        self.start_upload()
        self.restore_window_state()

    def setup_base_ui(self):
        """Setup basic UI components"""
        self.app_icon = QIcon(get_resource_path("Assets/logo_ipm.png"))
        self.setWindowIcon(self.app_icon)
        self.setMinimumSize(800, 600)
        ui_path = get_resource_path("UI/main.ui")
        loadUi(ui_path, self)
        self.labelInfo.setText("AIS Viewer")

    def setup_thread_management(self):
        """Setup thread management"""
        self.receiver_worker = None
        self.sender_worker = None
        self.upload_worker = None

        self.toggleReceiver = False
        self.toggleSender = False

        self.stop_receiver_event = threading.Event()
        self.stop_sender_event = threading.Event()
        self.stop_upload_event = threading.Event()

    def setup_system_tray(self):
        """Setup system tray icon and menu"""
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
        """Connect signals to slots"""
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
        """Setup status bar with better layout"""
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(20)

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

        self.statusbar.addPermanentWidget(status_widget, 1)

    def setup_error_logging(self):
        """Setup error logging with buffer and timer"""
        self.error_buffer = []
        self.error_timer = QTimer()
        self.error_timer.setInterval(1000)
        self.error_timer.timeout.connect(self.flush_error_buffer)
        self.error_timer.start()

    def flush_error_buffer(self):
        """Flush error buffer to log file"""
        for msg in self.error_buffer:
            error_file_logger.error(msg)
        self.error_buffer.clear()

    def restore_window_state(self):
        """Load window size and position from previous session"""
        settings = QSettings("IPM", "SeaScope_Receiver")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1000, 700)

    def save_window_state(self):
        """Save window size and position"""
        settings = QSettings("IPM", "SeaScope_Receiver")
        settings.setValue("geometry", self.saveGeometry())

    def update_logger(self, message):
        """Update log in main logger tab"""
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
        """Update log in error tab"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_message = f"{timestamp} - 🚨 ERROR: {message}"

        # Set emoji font
        emoji_font = QFont("Noto Color Emoji")
        emoji_font.setPointSize(10)
        self.plainTextError.setFont(emoji_font)
        self.plainTextError.appendPlainText(error_message)
        self.update_logger(f"🚨 ERROR: {message}")
        self.error_buffer.append(message)
        if self.plainTextError.blockCount() > self.MAX_LOG_ITEMS:
            current_text = self.plainTextError.toPlainText()
            new_text = '\n'.join(current_text.split('\n')[1:])
            self.plainTextError.setPlainText(new_text)
        self.plainTextError.verticalScrollBar().setValue(
            self.plainTextError.verticalScrollBar().maximum()
        )

    def update_info(self, message):
        """Update log with info message"""
        self.update_logger(f"ℹ️ INFO: {message}")
        self.labelInfo.setText(message)

    def update_warning(self, message):
        """Update log with warning message"""
        self.update_logger(f"⚠️ WARNING: {message}")

    def create_progress_dialog(self, message, with_cancel=False):
        """Helper method to create progress dialog with consistent look"""
        progress_dialog = QProgressDialog(message, "Cancel" if with_cancel else None, 0, 0, self)
        progress_dialog.setWindowTitle("Please Wait - NMEA Receiver")
        progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress_dialog.setMinimumDuration(500)
        progress_dialog.setMinimumWidth(350)

        progress_bar = progress_dialog.findChild(QProgressBar)
        if progress_bar:
            progress_bar.setTextVisible(False)
            progress_bar.setMaximum(0)
            progress_bar.setMinimumHeight(15)

        if not with_cancel:
            cancel_button = progress_dialog.findChild(QPushButton)
            if cancel_button:
                cancel_button.hide()

        return progress_dialog

    def start_upload(self):
        """Start upload service"""
        self.stop_upload_event.clear()
        self.upload_worker = UploadWorker(self.stop_upload_event)
        self.upload_worker.start()
        self.UploadLabel.setText("Upload: Running")
        self.UploadLabel.setStyleSheet("QLabel { color: green; font-weight: bold; }")
        self.statusbar.showMessage('Upload Service Started', self.STATUS_MESSAGE_TIMEOUT)

    def stop_upload(self):
        """Stop upload service"""
        if hasattr(self, 'upload_worker') and self.upload_worker and self.upload_worker.isRunning():
            self.stop_upload_event.set()
            self.upload_worker.quit()
            self.upload_worker.wait()
            self.upload_worker = None
            self.UploadLabel.setText("Upload: Stopped")
            self.UploadLabel.setStyleSheet("")
            self.statusbar.showMessage('Upload Service Stopped', self.STATUS_MESSAGE_TIMEOUT)

    def start_receiver(self):
        """Run AIS receiver in separate thread"""
        if not hasattr(self, 'receiver_worker') or not self.receiver_worker or not self.receiver_worker.isRunning():
            progress_dialog = self.create_progress_dialog("Starting receiver service...")
            progress_dialog.show()

            self.stop_receiver_event.clear()
            self.receiver_worker = ReceiverWorker(self.stop_receiver_event)
            self.receiver_worker.start()

            self.actionRun_Receiver.setEnabled(False)
            self.actionStop_Receiver.setEnabled(True)
            self.run_receiver_action.setEnabled(False)
            self.stop_receiver_action.setEnabled(True)
            self.toggleReceiver = True
            self.ReceiverLabel.setText("Receiver: Running")
            self.ReceiverLabel.setStyleSheet("QLabel { color: green; font-weight: bold; }")

            QTimer.singleShot(1000, progress_dialog.close)
            self.statusbar.showMessage('Receiver Started', self.STATUS_MESSAGE_TIMEOUT)

    def stop_receiver(self):
        """Stop AIS receiver"""
        if hasattr(self, 'receiver_worker') and self.receiver_worker and self.receiver_worker.isRunning():
            progress_dialog = self.create_progress_dialog("Stopping receiver service...")
            progress_dialog.show()

            self.stop_receiver_event.set()
            self.receiver_worker.quit()
            self.receiver_worker.wait()
            self.receiver_worker = None

            self.actionRun_Receiver.setEnabled(True)
            self.actionStop_Receiver.setEnabled(False)
            self.run_receiver_action.setEnabled(True)
            self.stop_receiver_action.setEnabled(False)
            self.toggleReceiver = False
            self.ReceiverLabel.setText("Receiver: Stopped")
            self.ReceiverLabel.setStyleSheet("")

            QTimer.singleShot(1000, progress_dialog.close)
            self.statusbar.showMessage('Receiver Stopped', self.STATUS_MESSAGE_TIMEOUT)

    def start_sender(self):
        """Run AIS sending to OpenCPN in separate thread"""
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
            self.toggleSender = True
            self.SenderLabel.setText("Sender: Running")
            self.SenderLabel.setStyleSheet("QLabel { color: green; font-weight: bold; }")

            QTimer.singleShot(1000, progress_dialog.close)
            self.statusbar.showMessage('Sender Started', self.STATUS_MESSAGE_TIMEOUT)

    def stop_sender(self):
        """Stop sending AIS to OpenCPN"""
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
            self.toggleSender = False
            self.SenderLabel.setText("Sender: Stopped")
            self.SenderLabel.setStyleSheet("")

            QTimer.singleShot(1000, progress_dialog.close)
            self.statusbar.showMessage('Sender Stopped', self.STATUS_MESSAGE_TIMEOUT)

    def closeEvent(self, event):
        """Handle event when main window is closed"""
        self.save_window_state()
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "NMEA Receiver IPM",
            "Application is still running in system tray.",
            QSystemTrayIcon.MessageIcon.Information
        )

    def tray_icon_clicked(self, reason):
        """Show main window when tray icon is clicked"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_main_window()

    def open_app_clicked(self):
        """Show main window when 'Open App' menu item is clicked"""
        self.show_main_window()

    def show_main_window(self):
        """Helper to show main window"""
        self.show()
        self.raise_()
        self.activateWindow()

    def exit(self):
        """Close application completely with resource cleanup"""
        self.stop_upload()
        self.stop_receiver()
        self.stop_sender()
        self.save_window_state()
        if hasattr(self, 'error_timer') and self.error_timer.isActive():
            self.error_timer.stop()
        self.tray_icon.hide()
        QApplication.quit()

    def showConfigure(self):
        """Show configuration window with handling for service restart"""
        was_receiver_running = self.toggleReceiver
        self.stop_receiver()
        self.stop_upload()
        dlg = ConfigureWindow(self)
        dlg.data_saved.connect(self.start_upload)
        if was_receiver_running:
            dlg.data_saved.connect(self.start_receiver)

        dlg.exec()

    def showConnection(self):
        """Show connection window with handling for service restart"""
        was_receiver_running = self.toggleReceiver
        self.stop_receiver()
        dlg = ConnectionWindow(self)
        if was_receiver_running:
            dlg.data_saved.connect(self.start_receiver)

        dlg.exec()