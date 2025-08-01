# message_widgets.py
# © 2025 Colt McVey
# Custom widgets for displaying formatted chat messages.

import re
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTextBrowser, QPushButton,
    QHBoxLayout, QFrame, QApplication, QLabel, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
import markdown2
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter

class CodeBlockWidget(QFrame):
    """A widget that displays a block of code with action buttons."""
    insert_code_requested = Signal(str)
    add_to_scratchpad_requested = Signal(str) # The correct signal name

    def __init__(self, language: str, code: str):
        super().__init__()
        self.code_text = code
        self.language = language
        self.setObjectName("codeBlock")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        lang_label = QLabel(language if language else "code")
        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(self.copy_code)
        insert_button = QPushButton("Insert into Notebook")
        insert_button.clicked.connect(self.request_insert)
        save_as_button = QPushButton("Save As...")
        save_as_button.clicked.connect(self.save_code_as_file)
        add_to_scratchpad_button = QPushButton("Add to Scratchpad")
        add_to_scratchpad_button.clicked.connect(self.request_add_to_scratchpad)

        header_layout.addWidget(lang_label)
        header_layout.addStretch()
        header_layout.addWidget(copy_button)
        header_layout.addWidget(insert_button)
        header_layout.addWidget(add_to_scratchpad_button)
        header_layout.addWidget(save_as_button)

        self.code_browser = QTextBrowser()
        
        try:
            lexer = get_lexer_by_name(language, stripall=True)
        except:
            lexer = guess_lexer(code)

        formatter = HtmlFormatter(style='monokai', cssclass="codehilite", linenos='table', nobackground=True)
        highlighted_code = highlight(code, lexer, formatter)
        
        full_html = f"""<style>...</style>{highlighted_code}"""
        self.code_browser.setHtml(full_html)

        layout.addWidget(header)
        layout.addWidget(self.code_browser)

    def copy_code(self):
        QApplication.clipboard().setText(self.code_text)
        
    def request_insert(self):
        self.insert_code_requested.emit(self.code_text)

    def request_add_to_scratchpad(self):
        self.add_to_scratchpad_requested.emit(self.code_text)

    def save_code_as_file(self):
        extension_map = {"python": "py", "javascript": "js", "html": "html", "css": "css"}
        ext = extension_map.get(self.language, "txt")
        filter = f"{self.language.capitalize()} Files (*.{ext});;All Files (*)"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Code Snippet", f"snippet.{ext}", filter)
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.code_text)
            except IOError as e:
                print(f"Error saving file: {e}")

class AIMessageBubble(QWidget):
    """A widget that intelligently renders a full AI response with mixed content."""
    insert_code_requested = Signal(str)
    add_to_scratchpad_requested = Signal(str) # Relay signal

    def __init__(self, markdown_text: str):
        super().__init__()
        self.setObjectName("aiMessageBubble")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        parts = re.split(r"(```(?:\w+)?\n.*?\n```)", markdown_text, flags=re.DOTALL)
        
        for part in parts:
            if not part.strip():
                continue

            code_match = re.match(r"```(\w+)?\n(.*?)\n```", part, flags=re.DOTALL)
            
            if code_match:
                language = code_match.group(1) or ""
                code = code_match.group(2).strip()
                code_widget = CodeBlockWidget(language, code)
                code_widget.insert_code_requested.connect(self.insert_code_requested)
                code_widget.add_to_scratchpad_requested.connect(self.add_to_scratchpad_requested)
                main_layout.addWidget(code_widget)
            else:
                text_browser = QTextBrowser()
                text_browser.setOpenExternalLinks(True)
                html = markdown2.markdown(part, extras=["tables", "fenced-code-blocks", "cuddled-lists", "strike"])
                text_browser.setHtml(html)
                main_layout.addWidget(text_browser)
