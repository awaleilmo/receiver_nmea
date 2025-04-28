from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import Qt, QTimer
from Untils.path_helper import get_resource_path


class ProgressDialog(QDialog):
    def __init__(self, parent=None, message="Please wait..."):
        super().__init__(parent)
        self.setWindowTitle("Processing")
        self.setFixedSize(300, 150)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        layout = QVBoxLayout(self)
        self.label = QLabel(message)
        self.svg = QSvgWidget(get_resource_path("Assets/loading.svg"))
        self.svg.setFixedSize(64, 64)

        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.svg, alignment=Qt.AlignmentFlag.AlignCenter)

        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: None)
        self.timer.start(100)

    def closeEvent(self, event):
        event.ignore()