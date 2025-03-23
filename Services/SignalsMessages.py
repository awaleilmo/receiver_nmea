from PyQt6.QtCore import QObject, pyqtSignal

class ReceiverSignals(QObject):
    new_data_received = pyqtSignal(str)  # Sinyal untuk mengirim data baru

signals = ReceiverSignals()
