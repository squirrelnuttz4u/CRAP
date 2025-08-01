# file_browser.py
# © 2025 Colt McVey
# A dockable file browser for managing context files.

import os
import asyncio
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHBoxLayout, QFileDialog, QLabel
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from ui_utils import create_icon_from_svg, SVG_ICONS
from rag_manager import rag_manager # Import the new RAG manager

class FileBrowserWidget(QWidget):
    """
    A widget for managing a collection of files to be used as context.
    """
    context_files_changed = Signal(list)

    def __init__(self):
        super().__init__()
        self.files = {} # {file_path: content}
        self.setup_ui()

    def setup_ui(self):
        """Initializes the UI components and layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        toolbar_layout = QHBoxLayout()
        upload_button = QPushButton("Upload Files")
        upload_button.setIcon(create_icon_from_svg(SVG_ICONS["upload"]))
        upload_button.clicked.connect(self.upload_files)
        toolbar_layout.addWidget(upload_button)
        toolbar_layout.addStretch()

        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["Context Files"])
        self.file_tree.itemDoubleClicked.connect(self.remove_file)

        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(self.file_tree)
        main_layout.addWidget(QLabel("Double-click a file to remove it."))

    def upload_files(self):
        """Opens a dialog to select and load one or more files."""
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Upload Files", "", "All Files (*)")
        
        if not file_paths:
            return

        for path in file_paths:
            if path in self.files:
                continue
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                self.files[path] = content
                
                item = QTreeWidgetItem(self.file_tree, [os.path.basename(path)])
                item.setData(0, Qt.ItemDataRole.UserRole, path)
                item.setToolTip(0, f"Path: {path}\nDouble-click to remove.")

            except Exception as e:
                print(f"Error reading file {path}: {e}")
        
        self.emit_context_change()

    def remove_file(self, item: QTreeWidgetItem, column: int):
        """Removes a file from the context list."""
        full_path = item.data(0, Qt.ItemDataRole.UserRole)
        if full_path in self.files:
            del self.files[full_path]
        
        (item.parent() or self.file_tree.invisibleRootItem()).removeChild(item)
        
        self.emit_context_change()

    def emit_context_change(self):
        """Emits the signal with the current list of files and triggers re-indexing."""
        file_list = [{"path": path, "content": content} for path, content in self.files.items()]
        self.context_files_changed.emit(file_list)
        # Trigger the RAG system to re-index the new set of files
        asyncio.create_task(rag_manager.index_files(file_list))
