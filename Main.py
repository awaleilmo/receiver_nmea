import sys
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

from Pages.Main_page import AISViewer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    QApplication.setOrganizationName("Integra Corp")
    QApplication.setApplicationName("NMEA Receiver IPM")
    QApplication.setApplicationDisplayName("NMEA Receiver IPM")
    QApplication.setWindowIcon(QIcon("Assets/logo_ipm.png"))
    settings = QSettings("IPM", "SeaScope_Receiver")
    use_dark_theme = settings.value("use_dark_theme", False, type=bool)
    window = AISViewer()
    window.show()
    window.start_receiver()
    sys.exit(app.exec())