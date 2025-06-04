from PyQt6.QtWidgets import QDialog, QGroupBox, QGridLayout, QVBoxLayout, QWidget, QCheckBox, QLabel, QDialogButtonBox, \
    QMessageBox
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QFont
from PyQt6.uic import loadUi
from PyQt6.QtCore import pyqtSignal, QTimer
from Controllers.Connection_controller import get_connection, update_connection_status, delete_connection
from Pages.Add_Connection_page import AddConnectionWindow
from Services.SignalsMessages import signalsInfo, signalsError, signalsWarning
from Untils.path_helper import get_resource_path


class ConnectionWindow(QDialog):
    data_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_group = None
        ui_path = get_resource_path("UI/connection.ui")
        loadUi(ui_path, self)

        self.scrollArea.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scrollArea.setWidget(self.scroll_content)

        self.add_button.clicked.connect(self.AddConnectionWindow)
        self.edit_button.clicked.connect(self.EditConnectionWindow)
        self.remove_button.clicked.connect(self.RemoveConnectionWindow)

        self.connection_checkboxes = {}
        self.load_data()

        # Hubungkan tombol dengan fungsi masing-masing
        self.buttonBox.accepted.connect(self.save_changes)  # OK

    def load_data(self):
        self.selected_group = None
        self.edit_button.setEnabled(False)
        self.remove_button.setEnabled(False)
        self.add_button.setEnabled(True)

        self.connection_checkboxes = {}
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            data = get_connection()
            font = QFont()
            font.setPointSize(9)
            font.setBold(True)

            if not data or len(data) == 0:
                from Services.SignalsMessages import signalsInfo
                signalsInfo.new_data_received.emit("Tidak ada data koneksi yang ditemukan.")
                self.edit_button.setEnabled(False)
                self.remove_button.setEnabled(False)
                self.add_button.setEnabled(True)
                self.scroll_layout.addStretch()
                return
            #show dAta
            for con in data:
                group_box = QGroupBox()
                group_box.setStyleSheet("QGroupBox { border: 1px solid; border-radius: 5px; }")
                group_box.setProperty("connection_id", con["id"])
                group_box.setProperty("name", con["name"])
                group_box.setProperty("type", con["type"])
                group_box.setProperty("data_port", con["data_port"])
                group_box.setProperty("baudrate", con["baudrate"])
                group_box.setProperty("address", con["address"])
                group_box.setProperty("port", con["port"])
                group_box.setProperty("protocol", con["protocol"])
                group_box.setProperty("network", con["network"])
                layout = QGridLayout()

                # parsing data
                DType = QLabel(con["type"].upper())
                DName = QLabel(con["name"].upper())
                DDataPort = QLabel(con["data_port"])
                DBaudrate = QLabel(str(con["baudrate"]))

                DAddress = QLabel(con["address"])
                DPort = QLabel(con["port"])

                for label in [DName, DType, DAddress, DPort, DBaudrate, DDataPort]:
                    label.setFont(font)

                # Checkbox enable
                enable_checkbox = QCheckBox("Enable")
                enable_checkbox.setChecked(bool(con["active"]))
                enable_checkbox.stateChanged.connect(lambda state, cid=con["id"]: self.checkbox_changed(cid, state))
                self.connection_checkboxes[con["id"]] = enable_checkbox
                layout.addWidget(enable_checkbox, 0, 0)

                # Label Data
                layout.addWidget(QLabel("Name Connection"), 0, 1)
                layout.addWidget(QLabel("Type"), 0, 2)

                layout.addWidget(DName, 1, 1)
                layout.addWidget(DType, 1, 2)

                if con["type"] == "network":
                    DProtocol = QLabel(f"{con['protocol'].upper()} {con['network'].upper()}")
                    DProtocol.setFont(font)

                    layout.addWidget(QLabel("Protocol"), 0, 3)
                    layout.addWidget(QLabel("Network Address"), 0, 4)
                    layout.addWidget(QLabel("Network Port"), 0, 5)

                    layout.addWidget(DProtocol, 1, 3)
                    layout.addWidget(DAddress, 1, 4)
                    layout.addWidget(DPort, 1, 5)
                elif con["type"] == "serial":
                    DProtocol = QLabel(con["protocol"].upper())
                    DProtocol.setFont(font)

                    layout.addWidget(QLabel("Protocol"), 0, 3)
                    layout.addWidget(QLabel("Serial Port"), 0, 4)
                    layout.addWidget(QLabel("Baudrate"), 0, 5)

                    layout.addWidget(DProtocol, 1, 3)
                    layout.addWidget(DDataPort, 1, 4)
                    layout.addWidget(DBaudrate, 1, 5)

                # Tambahkan group box ke layout utama
                group_box.setLayout(layout)
                group_box.mousePressEvent = lambda event, gb=group_box: self.select_row(gb)
                self.scroll_layout.addWidget(group_box)

            self.scroll_layout.addStretch()
        except Exception as e:
            from Services.SignalsMessages import signalsError
            error_msg = f"Error saat memuat data koneksi: {str(e)}"
            signalsError.new_data_received.emit(error_msg)
            signalsError.new_data_received.emit(error_msg)
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

    def save_changes(self):
        try:
            for conn_id, checkbox in self.connection_checkboxes.items():
                try:
                    new_status = 1 if checkbox.isChecked() else 0
                    update_connection_status(conn_id, new_status)
                except Exception as e:
                    from Services.SignalsMessages import signalsError
                    error_msg = f"Error updating connection {conn_id}: {str(e)}"
                    signalsError.new_data_received.emit(error_msg)
                    signalsError.new_data_received.emit(error_msg)

            self.data_saved.emit()
            signalsInfo.new_data_received.emit("Perubahan data Connection telah disimpan.")

        except Exception as e:
            from Services.SignalsMessages import signalsError
            error_msg = f"Error saving changes: {str(e)}"
            signalsError.new_data_received.emit(error_msg)
            signalsError.new_data_received.emit(error_msg)

    def AddConnectionWindow(self):
        add_connection_window = AddConnectionWindow(self)
        add_connection_window.data_saved.connect(self.load_data)
        add_connection_window.exec()

    def EditConnectionWindow(self):
        if not self.selected_group:
            signalsInfo.new_data_received.emit("Tidak ada group yang dipilih.")
            return

        connection_data = {
            "id": self.selected_group.property("connection_id"),
            "name": self.selected_group.property("name"),
            "type": self.selected_group.property("type"),
            "data_port": self.selected_group.property("data_port"),
            "baudrate": self.selected_group.property("baudrate"),
            "protocol": self.selected_group.property("protocol"),
            "address": self.selected_group.property("address"),
            "port": self.selected_group.property("port"),
            "network": self.selected_group.property("network")
        }

        edit_connection_window = AddConnectionWindow(self, connection_data)
        edit_connection_window.data_saved.connect(self.load_data)
        edit_connection_window.exec()

    def RemoveConnectionWindow(self):
        if not self.selected_group:
            signalsInfo.new_data_received.emit("Tidak ada group yang dipilih.")
            return

        try:
            connection_id = self.selected_group.property("connection_id")
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
                connections = get_connection()
                for conn in connections:
                    if conn["id"] == connection_id and conn.get("active", 0) == 1:
                        update_connection_status(connection_id, 0)
                        break
            except Exception as e:
                signalsWarning.new_data_received.emit(f"Warning when deactivating: {e}")

            # Reset UI state sebelum haups database
            if connection_id in self.connection_checkboxes:
                del self.connection_checkboxes[connection_id]

            self.selected_group = None
            self.edit_button.setEnabled(False)
            self.remove_button.setEnabled(False)
            self.add_button.setEnabled(True)

            try:
                delete_connection(connection_id)
                signalsInfo.new_data_received.emit(f"Delete connection {connection_id} successful.")
            except Exception as e:
                signalsError.new_data_received.emit(f"Error saat menghapus koneksi dari database: {str(e)}")
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
            signalsError.new_data_received.emit(f"Error saat proses penghapusan koneksi: {str(e)}")

    def closeEvent(self, event):
        self.data_saved.emit()
        event.accept()
        self.close()