# debugger_widget.py
# © 2025 Colt McVey
# A dockable panel for the integrated debugger.

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QGroupBox, QHeaderView, QHBoxLayout, QPushButton
)
from PySide6.QtCore import Qt
from ui_utils import create_icon_from_svg, SVG_ICONS
from debugger_logic import DebuggerLogic

class DebuggerWidget(QWidget):
    """
    A widget that provides a UI for the debugging session, including
    call stack, variables, and breakpoints.
    """
    def __init__(self):
        super().__init__()
        self.debugger_logic = None
        self.setup_ui()

    def set_debugger_logic(self, logic: DebuggerLogic):
        """Connects the UI to a debugger logic instance."""
        self.debugger_logic = logic
        self.continue_button.clicked.connect(self.debugger_logic.continue_execution)
        self.step_over_button.clicked.connect(self.debugger_logic.step_over)
        self.step_in_button.clicked.connect(self.debugger_logic.step_in)
        self.step_out_button.clicked.connect(self.debugger_logic.step_out)
        
        self.debugger_logic.stopped.connect(self.on_stopped)
        self.debugger_logic.continued.connect(self.on_continued)
        self.debugger_logic.finished.connect(self.on_finished)

    def setup_ui(self):
        """Initializes the UI components and layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        # --- Controls ---
        controls_layout = QHBoxLayout()
        self.continue_button = QPushButton("Continue")
        self.step_over_button = QPushButton("Step Over")
        self.step_in_button = QPushButton("Step In")
        self.step_out_button = QPushButton("Step Out")
        
        controls_layout.addWidget(self.continue_button)
        controls_layout.addWidget(self.step_over_button)
        controls_layout.addWidget(self.step_in_button)
        controls_layout.addWidget(self.step_out_button)
        controls_layout.addStretch()
        self.set_controls_enabled(False)

        # --- Views ---
        variables_group = QGroupBox("Variables")
        variables_layout = QVBoxLayout(variables_group)
        self.variables_tree = QTreeWidget()
        self.variables_tree.setHeaderLabels(["Name", "Type", "Value"])
        self.variables_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        variables_layout.addWidget(self.variables_tree)
        
        callstack_group = QGroupBox("Call Stack")
        callstack_layout = QVBoxLayout(callstack_group)
        self.callstack_tree = QTreeWidget()
        self.callstack_tree.setHeaderLabels(["Frame", "File", "Line"])
        callstack_layout.addWidget(self.callstack_tree)

        breakpoints_group = QGroupBox("Breakpoints")
        breakpoints_layout = QVBoxLayout(breakpoints_group)
        self.breakpoints_tree = QTreeWidget()
        self.breakpoints_tree.setHeaderLabels(["File", "Line"])
        breakpoints_layout.addWidget(self.breakpoints_tree)

        main_layout.addLayout(controls_layout)
        main_layout.addWidget(variables_group, 1)
        main_layout.addWidget(callstack_group, 1)
        main_layout.addWidget(breakpoints_group, 1)

    def set_controls_enabled(self, enabled: bool):
        """Enables or disables the debugger control buttons."""
        self.continue_button.setEnabled(enabled)
        self.step_over_button.setEnabled(enabled)
        self.step_in_button.setEnabled(enabled)
        self.step_out_button.setEnabled(enabled)

    def on_stopped(self, stack: list, variables: list):
        self.set_controls_enabled(True)
        self.update_callstack(stack)
        self.update_variables(variables)

    def on_continued(self):
        self.set_controls_enabled(False)
        self.variables_tree.clear()
        self.callstack_tree.clear()
        
    def on_finished(self):
        self.on_continued() # Clear UI on finish

    def update_variables(self, variables: list):
        self.variables_tree.clear()
        for var in variables:
            QTreeWidgetItem(self.variables_tree, [var['name'], var['type'], var['value']])
        self.variables_tree.expandAll()

    def update_callstack(self, frames: list):
        self.callstack_tree.clear()
        for frame in frames:
            QTreeWidgetItem(self.callstack_tree, [frame['name'], frame['file'], str(frame['line'])])

    def update_breakpoints(self, breakpoints: list):
        self.breakpoints_tree.clear()
        for bp in breakpoints:
            QTreeWidgetItem(self.breakpoints_tree, [bp['file'], str(bp['line'])])
