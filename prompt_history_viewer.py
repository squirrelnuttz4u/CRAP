# prompt_history_viewer.py
# © 2025 Colt McVey
# A dialog for viewing the version history of a prompt.

import sys
import json
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QTextBrowser, QPushButton, QDialogButtonBox,
    QLabel
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

# Import the prompt management classes
from prompt_manager import Prompt, PromptVersion

class PromptHistoryViewer(QDialog):
    """
    A dialog to view the version history of a single prompt and revert to old versions.
    """
    # Signal emitted when the user wants to revert to a specific version
    version_selected_for_revert = Signal(dict)

    def __init__(self, prompt: Prompt, parent=None):
        super().__init__(parent)
        self.prompt = prompt
        self.setWindowTitle(f"History for: {self.prompt.name}")
        self.setMinimumSize(900, 600)
        self.setup_ui()
        self.populate_history_list()

    def setup_ui(self):
        """Initializes the UI components and layout."""
        main_layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- Left Panel: Commit List ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Commit History:"))
        self.history_list = QListWidget()
        self.history_list.currentItemChanged.connect(self.on_version_selected)
        left_layout.addWidget(self.history_list)
        
        # --- Right Panel: Version Details ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("Version Details:"))
        self.details_browser = QTextBrowser()
        self.details_browser.setFont(QFont("Courier New", 10))
        right_layout.addWidget(self.details_browser)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 600]) # Give more space to the details view

        main_layout.addWidget(splitter)

        # --- Buttons ---
        self.revert_button = QPushButton("Revert to this Version")
        self.revert_button.setEnabled(False)
        self.revert_button.clicked.connect(self.revert_to_selected)

        button_box = QDialogButtonBox()
        button_box.addButton(self.revert_button, QDialogButtonBox.ButtonRole.ActionRole)
        button_box.addButton(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject) # Close button connects to reject

        main_layout.addWidget(button_box)

    def populate_history_list(self):
        """Fills the list widget with all versions of the prompt."""
        # Sort versions by timestamp, newest first
        sorted_versions = sorted(self.prompt.versions.values(), key=lambda v: v.timestamp, reverse=True)
        
        for version in sorted_versions:
            # Display format: "Commit Message (short_hash)"
            item_text = f"{version.message} ({version.version_id[:7]})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, version.version_id) # Store full version ID
            
            # Highlight the HEAD version
            if self.prompt.head == version.version_id:
                item.setFont(QFont("Inter", 10, QFont.Weight.Bold))
                item.setText(f"HEAD: {item_text}")

            self.history_list.addItem(item)

    def on_version_selected(self, current_item: QListWidgetItem, previous_item: QListWidgetItem):
        """Displays the details of the selected version."""
        if not current_item:
            return
            
        version_id = current_item.data(Qt.ItemDataRole.UserRole)
        version = self.prompt.get_version(version_id)
        
        if version:
            details_html = f"""
            <strong>Version ID:</strong> {version.version_id}<br>
            <strong>Timestamp:</strong> {version.timestamp}<br>
            <strong>Commit Message:</strong> {version.message}<br>
            <hr>
            <strong>Prompt Data:</strong>
            <pre>{json.dumps(version.data, indent=2)}</pre>
            """
            self.details_browser.setHtml(details_html)
            self.revert_button.setEnabled(True)

    def revert_to_selected(self):
        """Emits a signal with the selected version's data and closes."""
        current_item = self.history_list.currentItem()
        if not current_item:
            return
            
        version_id = current_item.data(Qt.ItemDataRole.UserRole)
        version = self.prompt.get_version(version_id)
        
        if version:
            self.version_selected_for_revert.emit(version.data)
            self.accept() # Close the dialog
