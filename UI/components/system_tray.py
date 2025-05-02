from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal


class SystemTrayManager(QObject):
    # Signal untuk komunikasi dengan main window
    open_app_requested = pyqtSignal()
    run_receiver_requested = pyqtSignal()
    stop_receiver_requested = pyqtSignal()
    run_sender_requested = pyqtSignal()
    stop_sender_requested = pyqtSignal()
    run_upload_requested = pyqtSignal()
    stop_upload_requested = pyqtSignal()
    exit_requested = pyqtSignal()

    def __init__(self, app_icon, parent=None):
        super().__init__(parent)
        self.tray_icon = QSystemTrayIcon(parent)
        self.tray_icon.setIcon(app_icon)
        self.setup_menu()

    def setup_menu(self):
        """Membuat menu tray dengan semua aksi yang diperlukan"""
        menu = QMenu()

        # Action untuk menampilkan aplikasi
        self.open_action = menu.addAction("Open App")
        self.open_action.triggered.connect(self.open_app_requested.emit)

        menu.addSeparator()

        # Action untuk receiver
        self.run_receiver_action = menu.addAction("Run Receiver")
        self.stop_receiver_action = menu.addAction("Stop Receiver")
        self.run_receiver_action.triggered.connect(self.run_receiver_requested.emit)
        self.stop_receiver_action.triggered.connect(self.stop_receiver_requested.emit)

        # Action untuk sender
        self.run_sender_action = menu.addAction("Run Sender")
        self.stop_sender_action = menu.addAction("Stop Sender")
        self.run_sender_action.triggered.connect(self.run_sender_requested.emit)
        self.stop_sender_action.triggered.connect(self.stop_sender_requested.emit)

        # Action untuk uploader
        self.run_upload_action = menu.addAction("Run Uploader")
        self.stop_upload_action = menu.addAction("Stop Uploader")
        self.run_upload_action.triggered.connect(self.run_upload_requested.emit)
        self.stop_upload_action.triggered.connect(self.stop_upload_requested.emit)

        menu.addSeparator()

        # Action untuk exit
        self.exit_action = menu.addAction("Exit")
        self.exit_action.triggered.connect(self.exit_requested.emit)

        # Set icon untuk aksi
        icon_run = QIcon.fromTheme("media-playback-start")
        icon_stop = QIcon.fromTheme("media-playback-stop")

        self.run_receiver_action.setIcon(icon_run)
        self.stop_receiver_action.setIcon(icon_stop)
        self.run_sender_action.setIcon(icon_run)
        self.stop_sender_action.setIcon(icon_stop)
        self.run_upload_action.setIcon(icon_run)
        self.stop_upload_action.setIcon(icon_stop)

        # Set status awal
        self.set_actions_state(
            run_receiver=True,
            stop_receiver=False,
            run_sender=True,
            stop_sender=False,
            run_upload=True,
            stop_upload=False
        )

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._handle_tray_activation)

    def set_actions_state(self, **states):
        """Mengatur enable/disable untuk semua aksi"""
        self.run_receiver_action.setEnabled(states.get('run_receiver', True))
        self.stop_receiver_action.setEnabled(states.get('stop_receiver', False))
        self.run_sender_action.setEnabled(states.get('run_sender', True))
        self.stop_sender_action.setEnabled(states.get('stop_sender', False))
        self.run_upload_action.setEnabled(states.get('run_upload', True))
        self.stop_upload_action.setEnabled(states.get('stop_upload', False))

    def _handle_tray_activation(self, reason):
        """Menangani klik pada tray icon"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.open_app_requested.emit()

    def show(self):
        """Menampilkan tray icon"""
        self.tray_icon.show()

    def hide(self):
        """Menyembunyikan tray icon"""
        self.tray_icon.hide()

    def show_message(self, title, message, timeout=3000):
        """Menampilkan pesan notifikasi"""
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, timeout)