from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtGui import QIcon
from PyQt6.uic import loadUi

from Untils.path_helper import get_resource_path


class BaseMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_base_ui()

    def setup_base_ui(self):
        self.app_icon = QIcon(get_resource_path("Assets/logo_ipm.png"))
        self.setWindowIcon(self.app_icon)
        self.setMinimumSize(800, 600)
        ui_path = get_resource_path("UI/main.ui")
        loadUi(ui_path, self)
        self.labelInfo.setText("AIS Viewer")