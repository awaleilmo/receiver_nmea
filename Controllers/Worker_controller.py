from PyQt6.QtCore import QObject, pyqtSignal
from Workers.worker_manager import WorkerManager

class WorkerController(QObject):
    status_changed = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.worker_manager = WorkerManager()
        self.worker_manager.status_changed.connect(self.status_changed)

    def start_worker(self, worker_type, worker_class):
        self.worker_manager.start_worker(worker_type, worker_class)

    def stop_worker(self, worker_type, callback=None):
        self.worker_manager.stop_worker(worker_type, callback)

    def get_worker_status(self, worker_type):
        return self.worker_manager.get_worker_status(worker_type)

