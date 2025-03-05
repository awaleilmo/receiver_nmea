from PyQt6.QtWidgets import QDialog
from PyQt6.uic import loadUi
from Controllers.Configure_controller import get_config, update_config


class ConfigureWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi("UI/config.ui", self)

        config = get_config()
        self.cpnHost.setText(config['cpn_host'])
        self.cpnPort.setText(config['cpn_port'])
        self.apiServer.setText(config['api_server'])

        self.buttonBox.accepted.connect(self.save_config)

    def save_config(self):
        cpn_host = self.cpnHost.text()
        cpn_port = self.cpnPort.text()
        api_server = self.apiServer.text()

        try:
            update_config(cpn_host, cpn_port, api_server)
            self.close()
        except Exception as e:
            print(f"Error: {e}")