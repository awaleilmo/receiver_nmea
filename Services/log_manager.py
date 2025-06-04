from PyQt6.QtCore import QObject, pyqtSignal
from datetime import datetime
from PyQt6.QtGui import QFont

class LogManager(QObject):
    MAX_LOG_ITEMS = 500

    log_received = pyqtSignal(str)
    error_received = pyqtSignal(str)
    info_received = pyqtSignal(str)
    warning_received = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.error_buffer = []

    def log(self, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_received.emit(f"{timestamp} - {message}")

    def error(self, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.error_received.emit(f"{timestamp} - 🚨 ERROR: {message}")
        self.error_buffer.append(message)

    def info(self, message):
        self.info_received.emit(message)

    def warning(self, message):
        self.warning_received.emit(f"⚠️ WARNING: {message}")