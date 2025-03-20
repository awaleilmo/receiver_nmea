from PyQt6.QtWidgets import QDialog, QGroupBox, QGridLayout, QVBoxLayout, QWidget, QCheckBox, QLabel, QDialogButtonBox
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QFont
from PyQt6.uic import loadUi
from PyQt6.QtCore import pyqtSignal
from Controllers.Connection_controller import get_connection, update_connection_status, delete_connection
from Pages.Add_Connection_page import AddConnectionWindow

class ConnectionWindow(QDialog):
    data_saved = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_group = None
        loadUi("UI/connection.ui", self)

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
        self.buttonBox.rejected.connect(self.reject)  # Cancel
        apply_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(self.save_changes)

    def load_data(self):
        data = get_connection()
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)


        if not data:
            print("Tidak ada data yang ditemukan.")
            return

        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

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

    def select_row(self, group_box):
        if self.selected_group == group_box:  # Jika sudah dipilih, batalkan pilihan
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
        for conn_id, checkbox in self.connection_checkboxes.items():
            new_status = 1 if checkbox.isChecked() else 0
            update_connection_status(conn_id, new_status)
            self.data_saved.emit()
        print("Perubahan telah disimpan.")

    def AddConnectionWindow(self):
        add_connection_window = AddConnectionWindow(self)
        add_connection_window.data_saved.connect(self.load_data)
        add_connection_window.exec()

    def EditConnectionWindow(self):
        if not self.selected_group:
            print("Tidak ada group yang dipilih.")
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
            print("Tidak ada group yang dipilih.")
            return

        connection_id = self.selected_group.property("connection_id")
        delete_connection(connection_id)
        self.load_data()