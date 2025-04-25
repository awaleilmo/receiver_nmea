from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialog
from PyQt6.uic import loadUi

from Controllers.Sender_controller import update_sender, add_sender
from Untils.path_helper import get_resource_path


class AddSenderWindow(QDialog):
    data_saved = pyqtSignal(str)
    def __init__(self, parent=None, sender_data=None):
        super().__init__(parent)
        ui_path = get_resource_path("UI/add_sender.ui")
        loadUi(ui_path, self)

        self.sender_data = sender_data

        self.buttonBox.accepted.connect(self.saveData)

        if self.sender_data:
            self.loadData()
        else:
            self.set_default_values()

    def saveData(self):
        name = self.lineName.text()
        host = self.lineAddress.text()
        port = self.linePort.text()
        active = 1

        if self.sender_data:
            update_sender(self.sender_data['identity'], name, host, port, active)
        else:
            add_sender(name, host, port, active)

        self.data_saved.emit("Sender Save")
        self.close()

    def set_default_values(self):
        self.lineName.setText("Sender Name")
        self.lineAddress.setText("localhost")
        self.linePort.setText("10110")

    def loadData(self):
        self.lineName.setText(self.sender_data["name"])
        self.lineAddress.setText(self.sender_data["host"])
        self.linePort.setText(self.sender_data["port"])