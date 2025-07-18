# Workers/worker_manager.py
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import threading


class WorkerManager(QObject):
    status_changed = pyqtSignal(str, str)  # (worker_type, status)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.workers = {
            'receiver': {'worker': None, 'stop_event': threading.Event()},
            'sender': {'worker': None, 'stop_event': threading.Event()},
            'upload': {'worker': None, 'stop_event': threading.Event()},
            'background_upload': {'worker': None, 'stop_event': threading.Event()}
        }

    def start_worker(self, worker_type, worker_class):
        """Start worker dengan progress dialog terintegrasi"""
        if self.workers[worker_type]['worker'] and self.workers[worker_type]['worker'].isRunning():
            return

        self.workers[worker_type]['stop_event'].clear()
        self.workers[worker_type]['worker'] = worker_class(
            self.workers[worker_type]['stop_event']
        )
        self.workers[worker_type]['worker'].start()
        self.status_changed.emit(worker_type, 'running')

    def stop_worker(self, worker_type, callback=None):
        """Stop worker dengan proses asynchronous"""
        if not self.workers[worker_type]['worker'] or not self.workers[worker_type]['worker'].isRunning():
            if callback: callback()
            return

        self.workers[worker_type]['stop_event'].set()

        # Cek status setiap 100ms
        timer = QTimer(self)
        timer.timeout.connect(lambda: self._check_stop_status(worker_type, timer, callback))
        timer.start(100)

    def _check_stop_status(self, worker_type, timer, callback):
        if not self.workers[worker_type]['worker'].isRunning():
            timer.stop()
            self.workers[worker_type]['worker'] = None
            self.status_changed.emit(worker_type, 'stopped')
            if callback: callback()

    def stop_all(self):
        for worker_type in self.workers:
            self.stop_worker(worker_type)