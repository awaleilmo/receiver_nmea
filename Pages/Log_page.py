import os
import threading
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                             QWidget, QPushButton, QTextEdit, QLabel,
                             QTabWidget, QComboBox, QSpinBox, QCheckBox, QFileDialog)
from PyQt6.QtGui import QFont, QColor, QTextCursor

from Services.SignalsMessages import signalsLogger, signalsInfo
from Untils.logging_helper import sys_logger, error_file_logger


class LogViewerTab(QWidget):
    def __init__(self, parent=None, log_type="system"):
        super().__init__(parent)
        self.log_type = log_type
        self.log_file = "logSystem.log" if log_type == "system" else "error.log"
        self.log_path = os.path.join("logs", self.log_file)

        # Create layout
        layout = QVBoxLayout(self)

        # Create controls
        controls_layout = QHBoxLayout()

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_log_content)

        # Auto-refresh checkbox
        self.auto_refresh_cb = QCheckBox("Auto-refresh")
        self.auto_refresh_cb.stateChanged.connect(self.toggle_auto_refresh)

        # Refresh interval
        self.refresh_interval_label = QLabel("Interval (sec):")
        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setRange(1, 60)
        self.refresh_interval_spin.setValue(5)

        # View lines
        self.view_lines_label = QLabel("Lines to show:")
        self.view_lines_combo = QComboBox()
        self.view_lines_combo.addItems(["50", "100", "200", "500", "1000", "All"])
        self.view_lines_combo.currentIndexChanged.connect(self.load_log_content)

        # Clear log button
        self.clear_btn = QPushButton("Clear Log")
        self.clear_btn.clicked.connect(self.clear_log)

        # Export log button
        self.export_btn = QPushButton("Export Log")
        self.export_btn.clicked.connect(self.export_log)

        # Add controls to layout
        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addWidget(self.auto_refresh_cb)
        controls_layout.addWidget(self.refresh_interval_label)
        controls_layout.addWidget(self.refresh_interval_spin)
        controls_layout.addWidget(self.view_lines_label)
        controls_layout.addWidget(self.view_lines_combo)
        controls_layout.addWidget(self.clear_btn)
        controls_layout.addWidget(self.export_btn)
        controls_layout.addStretch()

        # Create text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 10))

        # Add components to main layout
        layout.addLayout(controls_layout)
        layout.addWidget(self.log_text)

        # Initialize auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_log_content)

        # Load initial content
        self.load_log_content()

    def load_log_content(self):
        try:
            if not os.path.exists(self.log_path):
                self.log_text.setPlainText(f"Log file not found: {self.log_path}")
                return

            with open(self.log_path, 'r', encoding='utf-8') as file:
                content = file.readlines()

            # Apply line limit if not "All"
            current_option = self.view_lines_combo.currentText()
            if current_option != "All":
                line_count = int(current_option)
                if len(content) > line_count:
                    content = content[-line_count:]

            # Apply highlighting
            self.log_text.clear()
            for line in content:
                self.format_log_line(line)

            # Scroll to the bottom
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.log_text.setTextCursor(cursor)

        except Exception as e:
            self.log_text.setPlainText(f"Error reading log file: {str(e)}")
            if self.log_type == "system":
                sys_logger.error(f"Error in log viewer: {str(e)}")
            else:
                error_file_logger.error(f"Error in log viewer: {str(e)}")

    def format_log_line(self, line):
        cursor = self.log_text.textCursor()
        format = cursor.charFormat()

        # Default color
        format.setForeground(QColor("black"))

        # Color based on log level
        if "ERROR" in line or "error" in line.lower() or "🚨" in line:
            format.setForeground(QColor("red"))
        elif "WARNING" in line or "warning" in line.lower() or "⚠️" in line:
            format.setForeground(QColor("orange"))
        elif "📡 Too many consecutive failures" in line:
            format.setForeground(QColor("red"))
        elif "INFO" in line or "info" in line.lower():
            format.setForeground(QColor("blue"))
        elif "SUCCESS" in line or "success" in line.lower() or "Successfully sent" in line:
            format.setForeground(QColor("green"))
        elif "API Response" in line:
            format.setForeground(QColor("purple"))
        elif "Processing" in line:
            format.setForeground(QColor("teal"))

        cursor.setCharFormat(format)
        cursor.insertText(line)

    def toggle_auto_refresh(self, state):
        if state == Qt.CheckState.Checked:
            interval_ms = self.refresh_interval_spin.value() * 1000
            self.refresh_timer.start(interval_ms)
        else:
            self.refresh_timer.stop()

    def clear_log(self):
        try:
            with open(self.log_path, 'w') as file:
                file.write("")
            self.load_log_content()
            message = f"Log file cleared: {self.log_file}"
            sys_logger.info(message)
            signalsInfo.new_data_received.emit(message)
        except Exception as e:
            self.log_text.setPlainText(f"Error clearing log file: {str(e)}")
            if self.log_type == "system":
                sys_logger.error(f"Error clearing log file: {str(e)}")
            else:
                error_file_logger.error(f"Error clearing log file: {str(e)}")

    def export_log(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Log", "", "Text Files (*.txt);;All Files (*)")

        if file_path:
            try:
                with open(self.log_path, 'r', encoding='utf-8') as source:
                    content = source.read()

                with open(file_path, 'w', encoding='utf-8') as target:
                    target.write(content)

                message = f"Log file exported: {self.log_file} to {file_path}"
                sys_logger.info(message)
                signalsInfo.new_data_received.emit(message)
            except Exception as e:
                self.log_text.setPlainText(f"Error exporting log file: {str(e)}")
                if self.log_type == "system":
                    sys_logger.error(f"Error exporting log file: {str(e)}")
                else:
                    error_file_logger.error(f"Error exporting log file: {str(e)}")

    def closeEvent(self, event):
        # Stop timer when widget is closed
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
        super().closeEvent(event)


class LogViewerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log Viewer")
        self.setMinimumSize(900, 600)

        # Create layout
        layout = QVBoxLayout(self)

        # Create tab widget
        self.tab_widget = QTabWidget()

        # Create system log tab
        self.system_log_tab = LogViewerTab(self, "system")
        self.tab_widget.addTab(self.system_log_tab, "System Log")

        # Create error log tab
        self.error_log_tab = LogViewerTab(self, "error")
        self.tab_widget.addTab(self.error_log_tab, "Error Log")

        # Add tab widget to layout
        layout.addWidget(self.tab_widget)

        # Close button
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

        # Log viewer message
        message = "Log viewer opened"
        sys_logger.info(message)
        signalsLogger.new_data_received.emit(message)

    def closeEvent(self, event):
        # Ensure timers are stopped when dialog is closed
        if hasattr(self, 'system_log_tab'):
            if self.system_log_tab.refresh_timer.isActive():
                self.system_log_tab.refresh_timer.stop()

        if hasattr(self, 'error_log_tab'):
            if self.error_log_tab.refresh_timer.isActive():
                self.error_log_tab.refresh_timer.stop()

        # Log closing message
        message = "Log viewer closed"
        sys_logger.info(message)
        signalsLogger.new_data_received.emit(message)

        super().closeEvent(event)