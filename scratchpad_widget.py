# scratchpad_widget.py
# © 2025 Colt McVey
# A dockable scratchpad for collecting and editing code snippets.

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QPushButton,
    QHBoxLayout, QFrame, QLabel
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class ScratchpadWidget(QWidget):
    """
    A widget that acts as a persistent text editor for code snippets and notes.
    """
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """Initializes the UI components and layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # --- Toolbar ---
        toolbar_layout = QHBoxLayout()
        self.clear_button = QPushButton("Clear Scratchpad")
        self.clear_button.clicked.connect(self.clear_text)
        toolbar_layout.addWidget(QLabel("<b>Scratchpad</b>"))
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.clear_button)

        # --- Text Editor ---
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Click 'Add to Scratchpad' on a code block in the AI Chat to send code here...")
        self.editor.setFont(QFont("Courier New", 10))

        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(self.editor)

    def append_text(self, code: str):
        """Appends a new block of code to the scratchpad."""
        current_text = self.editor.toPlainText()
        separator = "\n\n# --- New Snippet ---\n\n"
        
        if current_text.strip() == "":
            self.editor.setPlainText(code)
        else:
            self.editor.setPlainText(f"{current_text}{separator}{code}")
            
        # Scroll to the end
        self.editor.verticalScrollBar().setValue(self.editor.verticalScrollBar().maximum())

    def clear_text(self):
        """Clears the contents of the scratchpad."""
        self.editor.clear()
