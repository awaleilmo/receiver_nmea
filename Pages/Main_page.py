import sys
import threading
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QIcon, QFont, QPalette, QColor
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDialog, QSystemTrayIcon, QMenu, QLabel,
                             QVBoxLayout, QHBoxLayout, QWidget, QProgressDialog, QFrame, QSplitter, QProgressBar)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QRunnable, QThreadPool, QSettings, QTimer
from PyQt6.uic import loadUi
from PySide6.QtWidgets import QPushButton

from Untils.path_helper import get_resource_path

from Services import sender, receiver
from Pages.Config_page import ConfigureWindow
from Pages.Connection_page import ConnectionWindow
from Services.SignalsMessages import signalsLogger, signalsError, signalsInfo, signalsWarning


# Definisi class Worker untuk operasi berat yang tidak memblokir UI cause why not?
class Worker(QRunnable):
    class WorkerSignals(QObject):
        finished = pyqtSignal()
        error = pyqtSignal(str)
        result = pyqtSignal(object)
        progress = pyqtSignal(int)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = Worker.WorkerSignals()

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


class AISViewer(QMainWindow):
    MAX_LOG_ITEMS = 1000
    PROGRESS_TIMEOUT = 1500
    STATUS_MESSAGE_TIMEOUT = 5000

    def __init__(self):
        super().__init__()
        self.setup_base_ui()
        self.setup_thread_management() #thread pool dan variabel kontrol
        self.setup_system_tray()
        self.setup_signals() #Connect slot yang sesuai
        self.setup_status_bar() # Status bar yang di bawah
        self.setup_initial_data()
        self.start_upload()
        self.restore_window_state()

    def setup_base_ui(self):
        """Setup komponen UI dasar"""
        self.app_icon = QIcon(get_resource_path("Assets/logo_ipm.png"))
        self.setWindowIcon(self.app_icon)
        self.setMinimumSize(800, 600)
        ui_path = get_resource_path("UI/main.ui")
        loadUi(ui_path, self)
        self.labelInfo.setText("AIS Viewer")

    def setup_thread_management(self):
        """Setup management untuk thread dan threadpool"""
        self.threadpool = QThreadPool()
        self.receiver_threads = []
        self.sender_thread = None

        self.toggleReceiver = False
        self.toggleSender = False

        self.stop_receiver_event = threading.Event()
        self.stop_sender_event = threading.Event()
        self.stop_upload_event = threading.Event()

    def setup_system_tray(self):
        """Setup system tray icon dan menu"""
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
        """Connect signals dengan slots"""
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
        signalsLogger.new_data_received.connect(self.update_log)
        signalsError.new_data_received.connect(self.update_error_log)
        signalsInfo.new_data_received.connect(self.update_info_log)
        signalsWarning.new_data_received.connect(self.update_warning_log)

    def setup_status_bar(self):
        """Setup status bar dengan layout yang lebih baik"""
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

    def setup_initial_data(self):
        """Setup data awal dan model untuk listview"""
        # Model untuk logger
        self.list_model_logger = QStandardItemModel(self)
        self.listViewLogger.setModel(self.list_model_logger)

        self.list_model_error = QStandardItemModel(self)
        if hasattr(self, 'listViewLogger_2'):  # Pastikan komponen UI ada
            self.listViewLogger_2.setModel(self.list_model_error)

    def restore_window_state(self):
        """Memuat pengaturan ukuran dan posisi window dari session sebelumnya"""
        settings = QSettings("IPM", "SeaScope_Receiver")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1000, 700)

    def save_window_state(self):
        """Menyimpan pengaturan ukuran dan posisi window"""
        settings = QSettings("IPM", "SeaScope_Receiver")
        settings.setValue("geometry", self.saveGeometry())

    def update_log(self, message):
        """Update log pada main logger view dengan pembatasan jumlah item"""
        self.update_log_common(self.list_model_logger, self.listViewLogger, message)

    def update_error_log(self, message):
        """Update log pada error tab"""
        # Prefix untuk error messages
        error_message = f"🚨 ERROR: {message}"
        self.update_log_common(self.list_model_error, self.listViewLogger_2, error_message)
        self.update_log(error_message)

    def update_info_log(self, message):
        """Update log dengan info message pada main log"""
        info_message = f"ℹ️ INFO: {message}"
        self.update_log(info_message)

    def update_warning_log(self, message):
        """Update log dengan warning message pada main log"""
        warning_message = f"⚠️ WARNING: {message}"
        self.update_log(warning_message)

    def update_log_common(self, model, view, message):
        """Fungsi umum untuk update log dengan batasan jumlah item"""
        # Buat item baru
        item = QStandardItem(message)
        emoji_font = QFont("Noto Color Emoji")
        emoji_font.setPointSize(10)
        item.setFont(emoji_font)

        # Tambahkan ke model
        model.appendRow(item)

        # Batasi jumlah log entries
        while model.rowCount() > self.MAX_LOG_ITEMS:
            model.removeRow(0)

        # Auto-scroll ke item terbaru
        view.scrollToBottom()

    def create_progress_dialog(self, message, with_cancel=False):
        """Metode helper untuk membuat dialog progress dengan tampilan yang konsisten"""
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
        """Memulai service upload dengan progress indicator yang lebih baik"""
        self.progress_dialog = self.create_progress_dialog("Starting upload service...", with_cancel=True)
        self.progress_dialog.show()

        self.stop_upload_event.clear()
        worker = Worker(self.run_upload_service)
        worker.signals.finished.connect(self.on_upload_service_started)
        self.threadpool.start(worker)

    def run_upload_service(self):
        """Fungsi untuk worker menjalankan upload service"""
        from Services.uploader import send_batch_data
        upload_thread = threading.Thread(
            target=send_batch_data,
            args=(self.stop_upload_event,),
            daemon=True
        )
        upload_thread.start()
        return upload_thread

    def on_upload_service_started(self):
        """Callback ketika upload service berhasil dimulai"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        self.UploadLabel.setText("Upload: Running")
        self.UploadLabel.setStyleSheet("QLabel { color: green; font-weight: bold; }")
        self.statusbar.showMessage('Upload Service Started', self.STATUS_MESSAGE_TIMEOUT)

    def stop_upload(self):
        """Menghentikan upload service"""
        self.UploadLabel.setText("Upload: Stopped")
        self.stop_upload_event.set()
        self.statusbar.showMessage('Upload Service Stopped', self.STATUS_MESSAGE_TIMEOUT)

    def run_receiver_thread(self):
        """Worker function untuk menjalankan receiver di thread"""
        self.receiver_threads = receiver.start_multi_receiver(self.stop_receiver_event)

    def start_receiver(self):
        """Menjalankan penerima AIS di thread terpisah dengan progress indicator"""
        if not self.receiver_threads:
            self.progress_dialog = self.create_progress_dialog("Starting receiver service...")
            self.progress_dialog.show()
            self.stop_receiver_event.clear()
            worker = Worker(self.run_receiver_thread)
            worker.signals.finished.connect(self.on_receiver_service_started)
            self.threadpool.start(worker)

    def on_receiver_service_started(self):
        """Callback ketika receiver service berhasil dimulai"""
        self.progress_dialog.close()
        self.actionRun_Receiver.setEnabled(False)
        self.actionStop_Receiver.setEnabled(True)
        self.run_receiver_action.setEnabled(False)
        self.stop_receiver_action.setEnabled(True)
        self.toggleReceiver = True
        self.ReceiverLabel.setText("Receiver: Running")
        self.statusbar.showMessage('Receiver Started', self.STATUS_MESSAGE_TIMEOUT)

    def stop_receiver(self):
        """Menghentikan penerima AIS dengan progress indicator"""
        if self.receiver_threads:
            self.progress_dialog = self.create_progress_dialog("Stopping receiver service...")
            self.progress_dialog.show()
            self.stop_receiver_event.set()
            worker = Worker(self.clean_receiver_threads)
            worker.signals.finished.connect(self.on_receiver_service_stopped)
            self.threadpool.start(worker)

    def clean_receiver_threads(self):
        """Worker function untuk membersihkan thread receiver"""
        for thread in self.receiver_threads:
            thread.join(timeout=5)
        return True

    def on_receiver_service_stopped(self):
        """Callback ketika receiver service berhasil dihentikan"""
        self.progress_dialog.close()
        self.receiver_threads = []
        self.actionRun_Receiver.setEnabled(True)
        self.actionStop_Receiver.setEnabled(False)
        self.run_receiver_action.setEnabled(True)
        self.stop_receiver_action.setEnabled(False)
        self.toggleReceiver = False
        self.ReceiverLabel.setText("Receiver: Stopped")
        self.statusbar.showMessage('Receiver Stopped', self.STATUS_MESSAGE_TIMEOUT)

    def start_sender(self):
        """Menjalankan pengiriman AIS ke OpenCPN di thread terpisah"""
        if self.sender_thread is None or not self.sender_thread.is_alive():
            self.progress_dialog = self.create_progress_dialog("Starting sender service...")
            self.progress_dialog.show()
            self.stop_sender_event.clear()
            worker = Worker(self.run_sender)
            worker.signals.finished.connect(self.on_sender_service_started)
            self.threadpool.start(worker)

    def run_sender(self):
        """Worker function untuk menjalankan sender service"""
        self.sender_thread = threading.Thread(
            target=sender.send_ais_data,
            args=(self.stop_sender_event,),
            daemon=True
        )
        self.sender_thread.start()
        return self.sender_thread

    def on_sender_service_started(self):
        """Callback ketika sender service berhasil dimulai"""
        self.progress_dialog.close()
        self.actionRun_Sender_OpenCPN.setEnabled(False)
        self.actionStop_Sender_OpenCPN.setEnabled(True)
        self.run_sender_action.setEnabled(False)
        self.stop_sender_action.setEnabled(True)
        self.toggleSender = True
        self.SenderLabel.setText("Sender: Running")
        self.statusbar.showMessage('Sender Started', self.STATUS_MESSAGE_TIMEOUT)

    def clean_sender_thread(self):
        """Worker function untuk membersihkan thread sender"""
        if self.sender_thread:
            self.sender_thread.join(timeout=5)
        return True

    def on_sender_service_stopped(self):
        """Callback ketika sender service berhasil dihentikan"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()

        self.actionRun_Sender_OpenCPN.setEnabled(True)
        self.actionStop_Sender_OpenCPN.setEnabled(False)
        self.run_sender_action.setEnabled(True)
        self.stop_sender_action.setEnabled(False)
        self.toggleSender = False
        self.SenderLabel.setText("Sender: Stopped")
        self.SenderLabel.setStyleSheet("QLabel { color: black; }")
        self.statusbar.showMessage('Sender Stopped', self.STATUS_MESSAGE_TIMEOUT)

    def stop_sender(self):
        """Menghentikan pengiriman AIS ke OpenCPN"""
        if self.sender_thread and self.sender_thread.is_alive():
            self.progress_dialog = self.create_progress_dialog("Stopping sender service...")
            self.progress_dialog.show()
            self.stop_sender_event.set()
            worker = Worker(self.clean_sender_thread)
            worker.signals.finished.connect(self.on_sender_service_stopped)
            self.threadpool.start(worker)

    def closeEvent(self, event):
        """Menangani event ketika jendela utama ditutup"""
        self.save_window_state()
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "NMEA Receiver IPM",
            "Aplikasi masih berjalan di system tray.",
            QSystemTrayIcon.MessageIcon.Information
        )

    def tray_icon_clicked(self, reason):
        """Menampilkan jendela utama ketika ikon tray diklik"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_main_window()

    def open_app_clicked(self):
        """Menampilkan jendela utama ketika menu 'Open App' diklik"""
        self.show_main_window()

    def show_main_window(self):
        """Helper untuk menampilkan jendela utama"""
        self.show()
        self.raise_()
        self.activateWindow()

    def exit(self):
        """Menutup aplikasi sepenuhnya dengan pembersihan resources"""
        self.stop_upload()
        self.stop_receiver()
        self.stop_sender()
        self.save_window_state()
        self.tray_icon.hide()
        QApplication.quit()

    def showConfigure(self):
        """Menampilkan jendela konfigurasi dengan penanganan untuk restart services"""
        was_receiver_running = self.toggleReceiver
        self.stop_receiver()
        self.stop_upload()
        dlg = ConfigureWindow(self)
        dlg.data_saved.connect(self.start_upload)
        if was_receiver_running:
            dlg.data_saved.connect(self.start_receiver)

        dlg.exec()

    def showConnection(self):
        """Menampilkan jendela koneksi dengan penanganan untuk restart services"""
        was_receiver_running = self.toggleReceiver
        self.stop_receiver()
        dlg = ConnectionWindow(self)
        if was_receiver_running:
            dlg.data_saved.connect(self.start_receiver)

        dlg.exec()