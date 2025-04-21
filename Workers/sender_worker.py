from PyQt6.QtCore import QThread
from Services import sender

class SenderWorker(QThread):
    def __init__(self, stop_event):
        super().__init__()
        self.stop_event = stop_event

    def run(self):
        sender.send_ais_data(self.stop_event)
