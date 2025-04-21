from PyQt6.QtCore import QThread
from Services import receiver

class ReceiverWorker(QThread):
    def __init__(self, stop_event):
        super().__init__()
        self.stop_event = stop_event

    def run(self):
        threads = receiver.start_multi_receiver(self.stop_event)
        for t in threads:
            t.join()
