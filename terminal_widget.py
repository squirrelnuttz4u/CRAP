# terminal_widget.py
# © 2025 Colt McVey
# A dockable terminal panel for running shell commands.

import sys
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTextBrowser, QLineEdit
)
from PySide6.QtCore import Qt, QProcess
from PySide6.QtGui import QFont, QColor

class TerminalWidget(QWidget):
    """
    A widget that provides an integrated terminal experience.
    """
    def __init__(self):
        super().__init__()
        self.process = QProcess(self)
        self.setup_ui()
        self.start_shell()

    def setup_ui(self):
        """Initializes the UI components and layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.output_browser = QTextBrowser()
        self.output_browser.setFont(QFont("Courier New", 10))
        
        self.input_line = QLineEdit()
        self.input_line.setFont(QFont("Courier New", 10))
        self.input_line.returnPressed.connect(self.run_command)

        layout.addWidget(self.output_browser)
        layout.addWidget(self.input_line)

    def start_shell(self):
        """Starts a persistent shell process."""
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        
        if sys.platform == "win32":
            self.process.start("cmd.exe")
        else:
            self.process.start("/bin/bash")
            
        self.input_line.setFocus()

    def run_command(self):
        """Sends a command from the input line to the shell process."""
        command = self.input_line.text().strip()
        if not command:
            return
            
        self.output_browser.append(f"> {command}")
        self.input_line.clear()
        
        # Add a newline character to execute the command in the shell
        self.process.write(f"{command}\n".encode('utf-8'))

    def handle_stdout(self):
        """Handles standard output from the shell process."""
        data = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        self.output_browser.append(data.strip())

    def handle_stderr(self):
        """Handles standard error from the shell process."""
        data = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
        self.output_browser.append(f"<font color='red'>{data.strip()}</font>")

    def closeEvent(self, event):
        """Ensures the shell process is terminated when the widget is closed."""
        self.process.kill()
        super().closeEvent(event)
