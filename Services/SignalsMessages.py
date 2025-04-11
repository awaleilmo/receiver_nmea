from PyQt6.QtCore import QObject, pyqtSignal

class ReceiverSignalsLogger(QObject):
    new_data_received = pyqtSignal(str)

class ReceiverSignalsError(QObject):
    new_data_received = pyqtSignal(str)

class ReceiverSignalsWarning(QObject):
    new_data_received = pyqtSignal(str)

class ReceiverSignalsInfo(QObject):
    new_data_received = pyqtSignal(str)

class ReceiverSignalsDebug(QObject):
    new_data_received = pyqtSignal(str)

signalsLogger = ReceiverSignalsLogger()
signalsError = ReceiverSignalsError()
signalsWarning = ReceiverSignalsWarning()
signalsInfo = ReceiverSignalsInfo()
signalsDebug = ReceiverSignalsDebug()
