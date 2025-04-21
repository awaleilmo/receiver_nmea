from PyQt6.QtCore import QThread
from Services.uploader import send_batch_data

class UploadWorker(QThread):
    def __init__(self, stop_event):
        super().__init__()
        self.stop_event = stop_event

    def run(self):
        send_batch_data(self.stop_event)
