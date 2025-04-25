from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QGroupBox, QGridLayout, QLabel, QCheckBox, QWidget, QVBoxLayout, QMessageBox
from PyQt6.uic import loadUi
from PyQt6.QtCore import pyqtSignal
from Controllers.Configure_controller import get_config, update_config
from Controllers.Sender_controller import get_sender, update_sender_status, remove_sender
from Models import SenderModel
from Untils.path_helper import get_resource_path
from Pages.Add_Sender_page import AddSenderWindow


class ConfigureWindow(QDialog):
    data_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_group = None
        ui_path = get_resource_path("UI/config.ui")
        loadUi(ui_path, self)

        self.scrollArea.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scrollArea.setWidget(self.scroll_content)

        self.add_button.clicked.connect(self.AddWindow)
        self.edit_button.clicked.connect(self.EditWindow)
        self.remove_button.clicked.connect(self.RemoveWindow)

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
                layout.addWidget(QLabel("Name Sender"), 0, 1)

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

    def select_row(self, group_box):
        if self.selected_group == group_box:
            self.selected_group.setStyleSheet("QGroupBox { border: 1px solid; border-radius: 5px; }")
            self.selected_group = None
            self.edit_button.setEnabled(False)
            self.remove_button.setEnabled(False)
            self.add_button.setEnabled(True)
        else:
            if self.selected_group:
                self.selected_group.setStyleSheet("QGroupBox { border: 1px solid; border-radius: 5px; }")
            self.selected_group = group_box
            self.selected_group.setStyleSheet("QGroupBox { border: 2px solid skyblue; border-radius: 5px; }")
            self.edit_button.setEnabled(True)
            self.remove_button.setEnabled(True)
            self.add_button.setEnabled(False)

    def checkbox_changed(self, connection_id, state):
        self.connection_checkboxes[connection_id].setChecked(state)

    def AddWindow(self):
        add_connection_window = AddSenderWindow(self)
        add_connection_window.data_saved.connect(self.load_data)
        add_connection_window.exec()

    def EditWindow(self):
        if not self.selected_group:
            print("Tidak ada data yang ditemukan.")
            return

        sender_data = {
            "identity": self.selected_group.property("identity"),
            "name": self.selected_group.property("name"),
            "host": self.selected_group.property("host"),
            "port": self.selected_group.property("port"),
        }

        edit_window = AddSenderWindow(self, sender_data)
        edit_window.data_saved.connect(self.load_data)
        edit_window.exec()

    def RemoveWindow(self):
        if not self.selected_group:
            print("Tidak ada data yang ditemukan.")
            return

        try:
            connection_id = self.selected_group.property("identity")
            connection_name = self.selected_group.property("name")
            widget_to_remove = self.selected_group
            widget_index = -1

            for i in range(self.scroll_layout.count()):
                if self.scroll_layout.itemAt(i).widget() == widget_to_remove:
                    widget_index = i
                    break

            # messagebox confirmation
            confirm = QMessageBox.question(
                self,
                "Konfirmasi Penghapusan",
                f"Apakah Anda yakin ingin menghapus koneksi '{connection_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if confirm != QMessageBox.StandardButton.Yes:
                return

            # Nonaktifkan koneksi jika aktif
            try:
                connections = get_sender()
                for conn in connections:
                    if conn["id"] == connection_id and conn.get("active", 0) == 1:
                        update_sender_status(connection_id, 0)
                        break
            except Exception as e:
                print(f"Warning when deactivating: {e}")

            # Reset UI state sebelum haups database
            if connection_id in self.connection_checkboxes:
                del self.connection_checkboxes[connection_id]

            self.selected_group = None
            self.edit_button.setEnabled(False)
            self.remove_button.setEnabled(False)
            self.add_button.setEnabled(True)

            try:
                remove_sender(connection_id)
                print(f"Delete connection {connection_id} successful.")
            except Exception as e:
                print(f"Error saat menghapus koneksi dari database: {str(e)}")
                return

            # Hpaus widget koneksi dari UI
            if widget_index >= 0:
                item = self.scroll_layout.takeAt(widget_index)
                if item and item.widget():
                    item.widget().deleteLater()

            remaining_connections = 0
            for i in range(self.scroll_layout.count()):
                item = self.scroll_layout.itemAt(i)
                if item and item.widget() and isinstance(item.widget(), QGroupBox):
                    remaining_connections += 1

            if remaining_connections == 0 and self.scroll_layout.count() == 0:
                self.scroll_layout.addStretch()

            self.data_saved.emit()

        except Exception as e:
            print(f"Error saat proses penghapusan koneksi: {str(e)}")
