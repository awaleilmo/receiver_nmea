from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import Qt, QTimer
from Untils.path_helper import get_resource_path


class ProgressDialog(QDialog):
    def __init__(self, parent=None, message="Please wait..."):
        super().__init__(parent)
        self.setWindowTitle("Processing")
        self.setModal(True)
        self.setFixedSize(300, 150)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.CustomizeWindowHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10,10,10,10)
        layout.setSpacing(10)

        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        svg = QSvgWidget(get_resource_path("Assets/loading.svg"))
        svg.setFixedSize(64, 64)
        layout.addWidget(svg, alignment=Qt.AlignmentFlag.AlignCenter)

        timer = QTimer(self)
        timer.timeout.connect(lambda: None)
        timer.start(100)


    def closeEvent(self, event):
        event.ignore()