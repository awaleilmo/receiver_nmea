from PyQt6.QtCore import QThread
from Services import receiver
from Services.SignalsMessages import signalsError


class ReceiverWorker(QThread):
    def __init__(self, stop_event):
        super().__init__()
        self.stop_event = stop_event

    def run(self):
        try:
            threads = receiver.start_multi_receiver(self.stop_event)
            while not self.stop_event.is_set():
                alive_threads = [t for t in threads if t.is_alive()]
                if not alive_threads:
                    break
                self.msleep(500)
        except Exception as e:
            self.stop_event.set()
            signalsError.new_data_received.emit(f"Receiver worker error: {str(e)}")
        finally:
            signalsError.new_data_received.emit("Receiver worker stopped.")
