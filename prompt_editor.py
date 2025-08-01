# prompt_editor.py
# © 2025 Colt McVey
# A sophisticated dialog for editing and engineering version-controlled prompts.

import sys
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QDialogButtonBox, QGroupBox,
    QTextEdit, QCheckBox, QTabWidget, QWidget, QFormLayout,
    QPushButton, QHBoxLayout, QListWidget, QListWidgetItem, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Import the prompt management classes and the history viewer
from prompt_manager import prompt_manager, Prompt
from prompt_history_viewer import PromptHistoryViewer

class PromptEditorDialog(QDialog):
    """
    A dialog window for structured prompt engineering with version control.
    """
    def __init__(self, prompt_name: str, parent=None):
        super().__init__(parent)
        self.prompt = prompt_manager.get_prompt(prompt_name)
        self.setWindowTitle(f"Prompt Editor: {prompt_name}")
        self.setMinimumSize(800, 700)
        self.setup_ui()
        self.load_prompt_data()

    def setup_ui(self):
        """Initializes the UI components and layout."""
        main_layout = QVBoxLayout(self)

        # --- Top Toolbar for History ---
        toolbar = QHBoxLayout()
        self.history_button = QPushButton("View History...")
        self.history_button.clicked.connect(self.open_history_viewer)
        toolbar.addStretch()
        toolbar.addWidget(self.history_button)
        main_layout.addLayout(toolbar)

        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # Tab 1: Core Prompt
        core_tab = QWidget()
        core_layout = QVBoxLayout(core_tab)
        instruction_group = QGroupBox("Instruction")
        instruction_layout = QVBoxLayout(instruction_group)
        self.instruction_edit = QTextEdit()
        instruction_layout.addWidget(self.instruction_edit)
        context_group = QGroupBox("Context / Data")
        context_layout = QVBoxLayout(context_group)
        self.context_edit = QTextEdit()
        context_layout.addWidget(self.context_edit)
        core_layout.addWidget(instruction_group)
        core_layout.addWidget(context_group)
        tab_widget.addTab(core_tab, "Core Prompt")

        # --- Dialog Buttons ---
        self.button_box = QDialogButtonBox()
        self.commit_button = self.button_box.addButton("Commit Changes", QDialogButtonBox.ButtonRole.AcceptRole)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.commit_button.clicked.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def open_history_viewer(self):
        """Opens the dialog to view the prompt's version history."""
        viewer = PromptHistoryViewer(self.prompt, self)
        viewer.version_selected_for_revert.connect(self.load_prompt_data)
        viewer.exec()

    def load_prompt_data(self, prompt_data: dict = None):
        """
        Loads prompt data into the UI. If no data is provided,
        it loads the latest version from the prompt object.
        """
        if prompt_data is None:
            latest_version = self.prompt.get_latest_version()
            if latest_version:
                prompt_data = latest_version.data
            else:
                prompt_data = {} # New prompt

        self.instruction_edit.setPlainText(prompt_data.get("instruction", ""))
        self.context_edit.setPlainText(prompt_data.get("context", ""))

    def get_prompt_data_from_ui(self) -> dict:
        """Collects all data from the UI and returns it as a dictionary."""
        return {
            "instruction": self.instruction_edit.toPlainText(),
            "context": self.context_edit.toPlainText(),
        }

    def accept(self):
        """
        Overrides the default accept behavior to handle committing a new version.
        """
        prompt_data = self.get_prompt_data_from_ui()
        
        latest_version = self.prompt.get_latest_version()
        if latest_version and latest_version.data == prompt_data:
            super().accept() # Close without committing
            return

        commit_message, ok = QInputDialog.getText(self, "Commit Prompt", "Enter a brief description of your changes:")
        
        if ok and commit_message:
            self.prompt.commit(prompt_data, commit_message)
            super().accept()
