from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QGroupBox, QGridLayout, QLabel, QCheckBox, QWidget, QVBoxLayout
from PyQt6.uic import loadUi
from PyQt6.QtCore import pyqtSignal
from Controllers.Configure_controller import get_config, update_config
from Controllers.Sender_controller import get_sender, update_sender_status
from Untils.path_helper import get_resource_path


class ConfigureWindow(QDialog):
    data_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        ui_path = get_resource_path("UI/config.ui")
        loadUi(ui_path, self)

        self.scrollArea.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scrollArea.setWidget(self.scroll_content)

        self.connection_checkboxes = {}

        config = get_config()
        self.apiServer.setText(config['api_server'])

        self.buttonBox.accepted.connect(self.save_config)

        self.load_data()

    def save_config(self):
        try:
            api_server = self.apiServer.text()

            for conn_id, checkbox in self.connection_checkboxes.items():
                try:
                    new_status = 1 if checkbox.isChecked() else 0
                    update_sender_status(conn_id, new_status)
                except Exception as e:
                    from Services.SignalsMessages import signalsError
                    error_msg = f"Error updating sender {conn_id}: {str(e)}"
                    signalsError.new_data_received.emit(error_msg)
                    print(error_msg)
            update_config(api_server)

            self.data_saved.emit()

        except Exception as e:
            from Services.SignalsMessages import signalsError
            error_msg = f"Error saving changes: {str(e)}"
            signalsError.new_data_received.emit(error_msg)
            print(error_msg)

    def load_data(self):
        self.connection_checkboxes = {}
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            data = get_sender()
            font = QFont()
            font.setPointSize(9)
            font.setBold(True)

            if not data or len(data) == 0:
                from Services.SignalsMessages import signalsInfo
                signalsInfo.new_data_received.emit("Tidak ada data Sender yang ditemukan.")
                print("Tidak ada data yang ditemukan.")
                self.edit_button.setEnabled(False)
                self.remove_button.setEnabled(False)
                self.add_button.setEnabled(True)
                self.scroll_layout.addStretch()
                return
            # show dAta
            for con in data:
                group_box = QGroupBox()
                group_box.setStyleSheet("QGroupBox { border: 1px solid; border-radius: 5px; }")
                group_box.setProperty("identity", con["id"])
                group_box.setProperty("name", con["name"])
                group_box.setProperty("host", con["host"])
                group_box.setProperty("port", con["port"])
                layout = QGridLayout()

                # parsing data
                DName = QLabel(con["name"].upper())
                DAddress = QLabel(con["host"])
                DPort = QLabel(con["port"])

                for label in [DName, DAddress, DPort]:
                    label.setFont(font)

                # Checkbox enable
                enable_checkbox = QCheckBox("Enable")
                enable_checkbox.setChecked(bool(con["active"]))
                enable_checkbox.stateChanged.connect(lambda state, cid=con["id"]: self.checkbox_changed(cid, state))
                self.connection_checkboxes[con["id"]] = enable_checkbox
                layout.addWidget(enable_checkbox, 0, 0)

                # Label Data
                layout.addWidget(QLabel("Name Connection"), 0, 1)

                layout.addWidget(DName, 1, 1)

                layout.addWidget(QLabel("Host"), 0, 2)
                layout.addWidget(QLabel("Port"), 0, 3)

                layout.addWidget(DAddress, 1, 2)
                layout.addWidget(DPort, 1, 3)

                # Tambahkan group box ke layout utama
                group_box.setLayout(layout)
                group_box.mousePressEvent = lambda event, gb=group_box: self.select_row(gb)
                self.scroll_layout.addWidget(group_box)

            self.scroll_layout.addStretch()
        except Exception as e:
            from Services.SignalsMessages import signalsError
            error_msg = f"Error saat memuat data koneksi: {str(e)}"
            signalsError.new_data_received.emit(error_msg)
            print(error_msg)
            self.scroll_layout.addStretch()

    def checkbox_changed(self, connection_id, state):
        self.connection_checkboxes[connection_id].setChecked(state)
