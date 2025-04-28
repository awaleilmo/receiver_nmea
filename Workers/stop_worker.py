from PyQt6.QtCore import QThread, pyqtSignal

class StopWorker(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, stop_receiver_event, stop_sender_event, stop_upload_event, parent=None):
        super().__init__(parent)
        self.stop_receiver = stop_receiver_event
        self.stop_sender = stop_sender_event
        self.stop_upload = stop_upload_event
        self.receiver_worker = None
        self.sender_worker = None
        self.upload_worker = None

    def set_workers(self, receiver_worker, sender_worker, upload_worker):
        self.receiver_worker = receiver_worker
        self.sender_worker = sender_worker
        self.upload_worker = upload_worker

    def run(self):
        try:
            if self.receiver_worker and self.receiver_worker.isRunning():
                self.stop_receiver.set()
                self.receiver_worker.quit()
                self.receiver_worker.wait()

            if self.sender_worker and self.sender_worker.isRunning():
                self.stop_sender.set()
                self.sender_worker.quit()
                self.sender_worker.wait()

            if self.upload_worker and self.upload_worker.isRunning():
                self.stop_upload.set()
                self.upload_worker.quit()
                self.upload_worker.wait()

            self.finished.emit()
        except Exception as e:
            self.error.emit(f"Error saat menghentikan worker: {str(e)}")