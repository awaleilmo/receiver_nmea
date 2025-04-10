from PyQt6.QtCore import pyqtSignal
from PyQt6.uic import loadUi
from PyQt6.QtWidgets import QDialog
import serial.tools.list_ports

from Controllers.Connection_controller import save_connection, update_connection
from Untils.path_helper import get_resource_path


class AddConnectionWindow(QDialog):
    data_saved = pyqtSignal()
    def __init__(self, parent=None, connection_data=None):
        super().__init__(parent)
        ui_path = get_resource_path("UI/add_connection.ui")
        loadUi(ui_path, self)

        self.connection_data = connection_data

        # Tambah baudrate ke combo box
        self.comboBaudrate.addItems(["300", "600", "1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"])
        self.comboBaudrate.setCurrentIndex(4)

        ports = serial.tools.list_ports.comports()

        for port in ports:
            self.comboDataPort.addItem(f"{port.device} - {port.description}", port.device)

        self.comboProtocol.addItem("NMEA 0183", "nmea0183")
        self.comboProtocol.addItem("NMEA 2000", "nmea2000")

        self.buttonBox.accepted.connect(self.saveData)
        self.buttonBox.rejected.connect(self.reject)

        # Hubungkan event radio button ke fungsi
        self.radioSerial.toggled.connect(self.on_radio_type_changed)
        self.radioNetwork.toggled.connect(self.on_radio_type_changed)

        if self.connection_data:
            self.load_connection_data()
        else:
            self.set_default_values()

        self.update_ui_visibility()

    def load_connection_data(self):
        self.lineName.setText(self.connection_data['name'])
        if self.connection_data["type"] == "serial":
            self.radioSerial.setChecked(True)
            baudrate_index = self.comboBaudrate.findText(self.connection_data["baudrate"])
            if baudrate_index != -1:
                self.comboBaudrate.setCurrentIndex(baudrate_index)
            else:
                print("Baudrate tidak ditemukan dalam ComboBox!")

            data_port_index = self.comboDataPort.findData(self.connection_data["data_port"])
            if data_port_index != -1:
                self.comboDataPort.setCurrentIndex(data_port_index)
            else:
                print("Data Port tidak ditemukan dalam ComboBox!")

        else:
            self.radioNetwork.setChecked(True)
            if(self.connection_data["network"] == "tcp"):
                self.radioTcp.setChecked(True)
            else:
                self.radioUdp.setChecked(True)
            self.lineAddress.setText(self.connection_data["address"])
            self.linePort.setText(str(self.connection_data["port"]))

        protocol_index = self.comboProtocol.findData(self.connection_data["protocol"])
        if protocol_index != -1:
            self.comboProtocol.setCurrentIndex(protocol_index)
        else:
            print("Protocol tidak ditemukan dalam ComboBox!")

    def on_radio_type_changed(self):
        self.update_ui_visibility()

    def update_ui_visibility(self):
        if self.radioSerial.isChecked():
            self.labelNetwork.hide()
            self.frameNetwork.hide()
            self.labelAddress.hide()
            self.lineAddress.hide()
            self.labelPort.hide()
            self.linePort.hide()

            self.labelBaudrate.show()
            self.comboBaudrate.show()
            self.labelDataPort.show()
            self.comboDataPort.show()
        elif self.radioNetwork.isChecked():
            self.labelNetwork.show()
            self.frameNetwork.show()
            self.labelAddress.show()
            self.lineAddress.show()
            self.labelPort.show()
            self.linePort.show()

            self.labelBaudrate.hide()
            self.comboBaudrate.hide()
            self.labelDataPort.hide()
            self.comboDataPort.hide()

    def set_default_values(self):
        self.lineName.setText("New Connection")
        self.radioSerial.setChecked(True)
        self.radioTcp.setChecked(True)
        self.lineAddress.setText("localhost")
        self.linePort.setText("10110")
        self.comboBaudrate.setCurrentIndex(4)
        self.comboDataPort.setCurrentIndex(0)

    def saveData(self):
        name = self.lineName.text()
        types = "serial" if self.radioSerial.isChecked() else "network"
        data_port = self.comboDataPort.itemData(self.comboDataPort.currentIndex())
        baudrate = self.comboBaudrate.currentText()
        protocol = self.comboProtocol.itemData(self.comboProtocol.currentIndex())
        network = "tcp" if self.radioTcp.isChecked() else "udp"
        address = self.lineAddress.text()
        port = self.linePort.text()
        active = 1

        if self.connection_data:
            update_connection(self.connection_data['id'], name, types, data_port, baudrate, protocol, network, address, port, active)
        else:
            save_connection(name, types, data_port, baudrate, protocol, network, address, port, active)

        self.data_saved.emit()
        self.close()