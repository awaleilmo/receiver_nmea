import sys
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from Pages.Main_page import AISViewer


if __name__ == "__main__":
    app = QApplication(sys.argv)
    QApplication.setOrganizationName("Integra Corp")
    QApplication.setApplicationName("NMEA Receiver IPM")
    QApplication.setApplicationDisplayName("NMEA Receiver IPM")
    QApplication.setWindowIcon(QIcon("Assets/logo_ipm.png"))
    window = AISViewer()
    window.show()
    sys.exit(app.exec())
