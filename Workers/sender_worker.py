import time
from PyQt6.QtCore import QThread
from Services import sender
from Services.SignalsMessages import signalsError, signalsInfo, signalsWarning
from Untils.logging_helper import sys_logger


class SenderWorker(QThread):
    def __init__(self, stop_event):
        super().__init__()
        self.stop_event = stop_event
        self.threads = []

    def run(self):
        try:
            self.threads = sender.start_multiple_senders(self.stop_event)
            while not self.stop_event.is_set():
                active_threads = [t for t in self.threads if t.is_alive()]
                if not active_threads:
                    break
                time.sleep(1)
        except Exception as e:
            sys_logger.error(f"Sender worker error: {str(e)}")
            self.stop_event.set()
        finally:
            sys_logger.info("Sender worker stopped.")
