from PyQt6.QtCore import QThread
from Services.uploader import send_batch_data
from Untils.logging_helper import sys_logger


class UploadWorker(QThread):
    def __init__(self, stop_event):
        super().__init__()
        self.stop_event = stop_event

    def run(self):
        sys_logger.info("Upload worker started")

        try:
            send_batch_data(self.stop_event)
        except Exception as e:
            sys_logger.error(f"Upload worker crashed: {str(e)}")
        finally:
            sys_logger.info("Upload worker stopped")
