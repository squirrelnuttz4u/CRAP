# notebook.py
# © 2025 Colt McVey
# The core notebook widget, with a robust and corrected AI task management system.

import sys
import os
import uuid
import json
import re
import networkx as nx
import ast
import asyncio
import logging
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QTextEdit, QTextBrowser, QPushButton, QToolBar, QScrollArea, QLabel,
    QMessageBox, QFileDialog, QCheckBox, QSizeGrip, QMenu
)
from PySide6.QtCore import Qt, QSize, Signal, QThread, QPoint, QObject
from PySide6.QtGui import QFont, QIcon, QAction, QColor, QTextCursor, QTextFormat, QPixmap, QPainter, QMouseEvent
from PySide6.QtSvg import QSvgRenderer

from collaboration_client import CollaborationClient
from kernel_manager import kernel_manager_service, NotebookKernel
from llm_interface import InferenceEngine
from ui_utils import create_icon_from_svg, SVG_ICONS
from settings_manager import settings_manager

# --- ANSI to HTML Conversion ---
def ansi_to_html(ansi_string: str):
    """Converts a string with ANSI escape codes to HTML with color styles."""
    color_map = {
        '30': 'black', '31': 'red', '32': 'green', '33': 'yellow',
        '34': 'blue', '35': 'magenta', '36': 'cyan', '37': 'white',
        '39': 'inherit' # Default color
    }
    
    ansi_escape_pattern = re.compile(r'\x1B\[((?:\d|;)*)m')
    
    html_output = ""
    last_end = 0
    open_span = False

    for match in ansi_escape_pattern.finditer(ansi_string):
        start, end = match.span()
        html_output += ansi_string[last_end:start]
        last_end = end
        
        codes = match.group(1).split(';')
        
        if open_span:
            html_output += '</span>'
            open_span = False
            
        if len(codes) == 1 and codes[0] in color_map:
            color = color_map[codes[0]]
            html_output += f'<span style="color:{color};">'
            open_span = True
        elif codes == ['0']:
            pass

    html_output += ansi_string[last_end:]
    if open_span:
        html_output += '</span>'
        
    return html_output.replace("\n", "<br>")


# --- Code Analysis ---
class CodeVisitor(ast.NodeVisitor):
    """
    Parses Python code using AST to find defined variables and dependencies.
    """
    def __init__(self):
        self.defined_vars = set()
        self.used_vars = set()

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.defined_vars.add(target.id)
        self.visit(node.value)

    def visit_FunctionDef(self, node):
        self.defined_vars.add(node.name)
        
    def visit_ClassDef(self, node):
        self.defined_vars.add(node.name)
        
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used_vars.add(node.id)
        self.generic_visit(node)

def analyze_code_dependencies(code):
    """
    Analyzes a string of Python code to find its inputs and outputs.
    """
    try:
        tree = ast.parse(code)
        visitor = CodeVisitor()
        visitor.visit(tree)
        dependencies = visitor.used_vars - visitor.defined_vars
        return visitor.defined_vars, dependencies
    except SyntaxError:
        return set(), set()

# --- Worker Threads ---
class ExecutionWorker(QThread):
    result_ready = Signal(dict)
    def __init__(self, kernel: NotebookKernel, code: str):
        super().__init__(); self.kernel = kernel; self.code = code
    def run(self):
        self.result_ready.emit(self.kernel.execute(self.code))

class AIGenerationThread(QThread):
    """A dedicated QThread to run an asyncio AI generation task."""
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, model_id: str, messages: list):
        super().__init__()
        self.model_id = model_id
        self.messages = messages

    async def _run_async(self):
        """The actual async part of the worker."""
        # Create a new engine instance within this thread's event loop.
        engine = InferenceEngine()
        streams = await engine.battle([self.model_id], self.messages)
        return "".join([token async for token in streams[0]])

    def run(self):
        """Runs the asyncio task in a new event loop on this thread."""
        try:
            result = asyncio.run(self._run_async())
            self.finished.emit(result)
        except Exception as e:
            logging.error(f"AI Generation Worker failed: {e}", exc_info=True)
            self.error.emit(str(e))

# --- Base Cell Classes ---
class BaseCell(QFrame):
    content_changed = Signal(object)
    delete_requested = Signal(str)
    cursor_activity = Signal(str, int, int)
    execution_requested = Signal(object)

    def __init__(self):
        super().__init__()
        self.cell_id = str(uuid.uuid4())
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)

        self.toolbar = QToolBar(); self.toolbar.setOrientation(Qt.Orientation.Vertical)
        
        content_and_resize_container = QWidget()
        container_layout = QVBoxLayout(content_and_resize_container)
        container_layout.setContentsMargins(0, 0, 0, 0); container_layout.setSpacing(0)

        self.content_widget = QWidget(); self.content_layout = QVBoxLayout(self.content_widget)
        
        resize_grip_layout = QHBoxLayout()
        resize_grip_layout.addStretch()
        self.resize_grip = QSizeGrip(self)
        resize_grip_layout.addWidget(self.resize_grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

        container_layout.addWidget(self.content_widget, 1)
        container_layout.addLayout(resize_grip_layout)

        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addWidget(content_and_resize_container, 1)
        
        delete_action = QAction(create_icon_from_svg(SVG_ICONS["delete"]), "Delete Cell", self)
        delete_action.setToolTip("Delete this cell.")
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.cell_id))
        self.toolbar.addAction(delete_action)

    def set_executing_state(self, is_executing: bool):
        if is_executing:
            self.setStyleSheet("QFrame { border: 1px solid #3498db; }")
        else:
            self.setStyleSheet("")

class TextEditorCell(BaseCell):
    def __init__(self):
        super().__init__()
        self.editor = None; self.remote_cursors = {}
        self._is_resizing = False; self._manual_height = None; self._resize_start_pos = QPoint()

    def setup_editor_signals(self):
        if self.editor:
            self.editor.cursorPositionChanged.connect(self.on_cursor_activity)
            self.editor.selectionChanged.connect(self.on_cursor_activity)
            self.editor.textChanged.connect(self._update_editor_height)
            self.editor.setMinimumHeight(40)

    def _update_editor_height(self):
        if self.editor and self._manual_height is None:
            doc_height = self.editor.document().size().height()
            new_height = doc_height + 15
            self.editor.setFixedHeight(max(40, int(new_height)))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() > self.height() - 10:
            self._is_resizing = True
            self._resize_start_pos = event.globalPosition()
            self._manual_height = self.editor.height()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_resizing:
            delta = event.globalPosition() - self._resize_start_pos
            new_height = self._manual_height + delta.y()
            if new_height > 40:
                self.editor.setFixedHeight(new_height)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._is_resizing:
            self._is_resizing = False
            self._manual_height = self.editor.height()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.position().y() > self.height() - 10:
            self._manual_height = None
            self._update_editor_height()
        super().mouseDoubleClickEvent(event)

    def on_cursor_activity(self):
        if not self.editor or self.editor.isReadOnly(): return
        cursor = self.editor.textCursor()
        self.cursor_activity.emit(self.cell_id, cursor.position(), cursor.anchor())

    def update_remote_cursor(self, client_id: str, cursor_pos: int, selection_end: int):
        if not self.editor: return
        extra_selections = [sel for cid, sel in self.remote_cursors.items() if cid != client_id]
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(get_color_for_client(client_id))
        cursor = self.editor.textCursor()
        cursor.setPosition(cursor_pos)
        if cursor_pos != selection_end:
             cursor.setPosition(selection_end, QTextCursor.MoveMode.KeepAnchor)
        else:
             selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = cursor
        extra_selections.append(selection)
        self.remote_cursors[client_id] = selection
        self.editor.setExtraSelections(extra_selections)

class MarkdownCell(TextEditorCell):
    def __init__(self, content=""):
        super().__init__()
        self.editor = QTextEdit(content); self.renderer = QTextBrowser()
        self.content_layout.addWidget(self.editor); self.content_layout.addWidget(self.renderer)
        self.setup_editor_signals()
        self.editor.textChanged.connect(self.on_text_changed)
        self.render_markdown()
        self._update_editor_height()

    def on_text_changed(self):
        if not self.editor.isReadOnly(): self.content_changed.emit(self)
        self.render_markdown()

    def get_content(self) -> str: return self.editor.toPlainText()
    def set_content(self, content: str, from_remote: bool = False):
        if from_remote: self.editor.setReadOnly(True)
        self.editor.setPlainText(content)
        if from_remote: self.editor.setReadOnly(False)
        self._update_editor_height()
    def render_markdown(self): self.renderer.setHtml(self.get_content().replace("\n", "<br>"))
    def to_dict(self) -> dict: return {"type": "markdown", "content": self.get_content()}

class CodeCell(TextEditorCell):
    execution_finished = Signal(str, dict)
    refactor_requested = Signal(object)
    generate_action_requested = Signal(object, str)

    def __init__(self, kernel, content=""):
        super().__init__()
        self.kernel = kernel
        self.execution_worker = None; self.is_test_cell = False
        self.defined_vars = set(); self.dependencies = set()
        
        self.editor = QTextEdit(content)
        self.output_area = QTextBrowser()
        
        header_layout = QHBoxLayout()
        self.test_checkbox = QCheckBox("Mark as Test")
        header_layout.addStretch()
        header_layout.addWidget(self.test_checkbox)
        
        self.content_layout.addLayout(header_layout)
        self.content_layout.addWidget(self.editor, 1)
        self.content_layout.addWidget(self.output_area)
        
        self.setup_editor_signals()
        self.test_checkbox.toggled.connect(self.on_test_checkbox_toggled)
        self.editor.textChanged.connect(self.on_text_changed)
        self.synchronize_test_state()
        self._update_editor_height()

        run_action = QAction(create_icon_from_svg(SVG_ICONS["run_cell"]), "Run Cell", self)
        run_action.setToolTip("Execute this cell and any other cells that depend on it.")
        run_action.triggered.connect(lambda: self.execution_requested.emit(self))
        self.toolbar.addAction(run_action)

    def contextMenuEvent(self, event):
        """Creates a right-click context menu for the code cell."""
        context_menu = QMenu(self)
        refactor_action = context_menu.addAction("Vibe Check: Refactor Code")
        context_menu.addSeparator()
        generate_tests_action = context_menu.addAction("Generate Tests")
        generate_docstring_action = context_menu.addAction("Generate Docstring")
        
        action = context_menu.exec(event.globalPos())
        
        if action == refactor_action:
            self.refactor_requested.emit(self)
        elif action == generate_tests_action:
            self.generate_action_requested.emit(self, "tests")
        elif action == generate_docstring_action:
            self.generate_action_requested.emit(self, "docstring")

    def on_text_changed(self):
        if not self.editor.isReadOnly():
            self.analyze()
            self.content_changed.emit(self)
        self.synchronize_test_state()

    def analyze(self):
        """Analyzes the code to find dependencies and defined variables."""
        self.defined_vars, self.dependencies = analyze_code_dependencies(self.get_content())

    def on_test_checkbox_toggled(self, is_checked):
        self.is_test_cell = is_checked
        self.editor.blockSignals(True)
        current_text = self.get_content()
        has_comment = current_text.lstrip().startswith("#| test")
        if is_checked and not has_comment:
            self.editor.setPlainText(f"#| test\n{current_text}")
        elif not is_checked and has_comment:
            lines = current_text.splitlines()
            if lines and lines[0].strip() == "#| test":
                self.editor.setPlainText("\n".join(lines[1:]))
        self.editor.blockSignals(False)
        self.update_style()
        self.content_changed.emit(self)

    def synchronize_test_state(self):
        has_comment = self.get_content().lstrip().startswith("#| test")
        self.test_checkbox.blockSignals(True)
        self.test_checkbox.setChecked(has_comment)
        self.test_checkbox.blockSignals(False)
        self.is_test_cell = has_comment
        self.update_style()

    def update_style(self):
        if self.is_test_cell: self.setStyleSheet("CodeCell { background-color: #2a3a2a; }")
        else: self.setStyleSheet("")

    def execute(self):
        self.set_executing_state(True)
        self.output_area.setText("Executing..."); self.output_area.show()
        self.execution_worker = ExecutionWorker(self.kernel, self.get_content())
        self.execution_worker.result_ready.connect(self.on_execution_complete)
        self.execution_worker.start()

    def on_execution_complete(self, result: dict):
        self.set_executing_state(False)
        self.output_area.clear()
        output_html = ""
        for item in result.get("outputs", []):
            text_content = ansi_to_html(item.get("text", ""))
            if item['type'] == 'error':
                output_html += f'<pre style="color:#e74c3c;">{text_content}</pre>'
            else:
                output_html += f'<pre>{text_content}</pre>'
        self.output_area.setHtml(output_html)
        self.execution_finished.emit(self.cell_id, result)

    def get_content(self) -> str: return self.editor.toPlainText()
    def set_content(self, content: str, from_remote: bool = False):
        if from_remote: self.editor.setReadOnly(True)
        self.editor.setPlainText(content)
        if from_remote: self.editor.setReadOnly(False)
        self.synchronize_test_state()
        self._update_editor_height()
    def to_dict(self) -> dict: return {"type": "code", "content": self.get_content()}

class NotebookWidget(QWidget):
    dirty_state_changed = Signal(bool)
    collaboration_status_updated = Signal(str)

    def __init__(self, notebook_id=None, file_path=None):
        super().__init__()
        self.notebook_id = notebook_id or str(uuid.uuid4())
        self.cells_by_id = {}; self.cell_order = []
        self.cell_layout = QVBoxLayout(); self._is_dirty = False; self.file_path = file_path
        self.kernel = kernel_manager_service.start_kernel_for_notebook(self.notebook_id)
        
        self.dep_graph = nx.DiGraph()
        self.execution_queue = []
        
        self.setup_ui(); self.apply_styles()
        self.collab_client = CollaborationClient(self.notebook_id)
        self.collab_client.message_received.connect(self.on_remote_change)
        self.collab_client.user_activity_received.connect(self.on_remote_user_activity)
        self.collab_client.connection_status_changed.connect(self.on_collab_status_changed)
        if self.file_path: self.load_from_file(self.file_path)
        else:
            self.add_cell('markdown', content="# Reactive Notebook\n\nChange a variable in one cell, and see dependent cells update automatically.")
            self.add_cell('code', content='a = 10')
            self.add_cell('code', content='b = 5')
            self.add_cell('code', content="c = a + b\nprint(f'The sum is {c}')")
            self.set_dirty(False)
            
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        toolbar = QToolBar()
        add_code_action = QAction(create_icon_from_svg(SVG_ICONS["add_code"]), "Add Code Cell", self)
        add_code_action.setToolTip("Add a new code cell to the end of the notebook.")
        add_code_action.triggered.connect(lambda: self.add_cell('code'))
        add_md_action = QAction(create_icon_from_svg(SVG_ICONS["add_md"]), "Add Markdown Cell", self)
        add_md_action.setToolTip("Add a new markdown cell to the end of the notebook.")
        add_md_action.triggered.connect(lambda: self.add_cell('markdown'))
        toolbar.addSeparator()
        run_all_action = QAction(create_icon_from_svg(SVG_ICONS["run_all"]), "Run All Cells", self)
        run_all_action.setToolTip("Execute all code cells in the notebook from top to bottom.")
        run_all_action.triggered.connect(self.run_all_cells)
        run_tests_action = QAction(create_icon_from_svg(SVG_ICONS["run_tests"]), "Run All Tests", self)
        run_tests_action.setToolTip("Execute only the cells marked as tests.")
        run_tests_action.triggered.connect(self.run_all_tests)
        toolbar.addSeparator()
        export_action = QAction(create_icon_from_svg(SVG_ICONS["export"]), "Export to Python Script", self)
        export_action.setToolTip("Export the notebook's code to a single Python file.")
        export_action.triggered.connect(self.export_to_script)
        toolbar.addAction(add_code_action); toolbar.addAction(add_md_action)
        toolbar.addAction(run_all_action); toolbar.addAction(run_tests_action)
        toolbar.addAction(export_action); main_layout.addWidget(toolbar)
        scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True)
        container_widget = QWidget(); container_widget.setLayout(self.cell_layout)
        scroll_area.setWidget(container_widget); main_layout.addWidget(scroll_area)

    def showEvent(self, event):
        if not self.collab_client.is_running: self.collab_client.start()
        super().showEvent(event)

    def run_all_cells(self):
        """Runs all code cells in the notebook in the correct topological order."""
        self.rebuild_dependency_graph()
        try:
            self.execution_queue = [self.cells_by_id[cell_id] for cell_id in nx.topological_sort(self.dep_graph) if cell_id in self.cells_by_id and isinstance(self.cells_by_id[cell_id], CodeCell)]
            self.execution_results = {}
            self._execute_next_in_queue()
        except nx.NetworkXUnfeasible:
            QMessageBox.critical(self, "Circular Dependency", "A circular dependency was detected in your notebook. Please correct the cell logic.")

    def on_cell_execution_requested(self, cell_to_run: CodeCell):
        """
        Handles a request to run a cell and all its downstream dependents.
        """
        self.rebuild_dependency_graph()
        try:
            descendants = nx.descendants(self.dep_graph, cell_to_run.cell_id)
            cells_to_run_ids = [cell_to_run.cell_id] + list(descendants)
            subgraph = self.dep_graph.subgraph(cells_to_run_ids)
            self.execution_queue = [self.cells_by_id[cell_id] for cell_id in nx.topological_sort(subgraph) if cell_id in self.cells_by_id]
            self.execution_results = {}
            self._execute_next_in_queue()
        except nx.NetworkXUnfeasible:
             QMessageBox.critical(self, "Circular Dependency", "A circular dependency was detected in your notebook. Please correct the cell logic.")

    def rebuild_dependency_graph(self):
        """Scans all cells and rebuilds the entire dependency graph."""
        self.dep_graph.clear()
        all_defined_vars = {}
        for cell_id in self.cell_order:
            cell = self.cells_by_id[cell_id]
            self.dep_graph.add_node(cell.cell_id)
            if isinstance(cell, CodeCell):
                cell.analyze()
                for var_name in cell.defined_vars:
                    all_defined_vars[var_name] = cell.cell_id
        for cell_id in self.cell_order:
            cell = self.cells_by_id[cell_id]
            if isinstance(cell, CodeCell):
                for dep_var in cell.dependencies:
                    if dep_var in all_defined_vars:
                        provider_cell_id = all_defined_vars[dep_var]
                        if provider_cell_id != cell_id:
                            self.dep_graph.add_edge(provider_cell_id, cell_id)
        print("Dependency graph rebuilt.")

    def add_cell(self, cell_type: str, content="", cell_id=None, from_remote=False, at_index=-1):
        if cell_type == 'code':
            cell = CodeCell(self.kernel, content)
            cell.refactor_requested.connect(self.on_refactor_requested)
            cell.generate_action_requested.connect(self.on_generate_action_requested)
        else:
            cell = MarkdownCell(content)
            
        new_cell_id = cell_id or cell.cell_id; cell.cell_id = new_cell_id
        cell.content_changed.connect(self.on_cell_content_changed)
        cell.delete_requested.connect(self.delete_cell)
        cell.cursor_activity.connect(self.on_local_cursor_activity)
        cell.execution_requested.connect(self.on_cell_execution_requested)
        
        if at_index == -1 or at_index >= len(self.cell_order):
            self.cells_by_id[new_cell_id] = cell; self.cell_order.append(new_cell_id)
            self.cell_layout.addWidget(cell)
        else:
            self.cells_by_id[new_cell_id] = cell; self.cell_order.insert(at_index, new_cell_id)
            self.cell_layout.insertWidget(at_index, cell)

        if not from_remote:
            self.set_dirty(True)
            self.rebuild_dependency_graph()
            message = {"type": "add_cell", "cell_id": cell.cell_id, "cell_type": cell_type, "content": content, "index": self.cell_order.index(new_cell_id)}
            self.collab_client.send_message(message)

    def on_cell_content_changed(self, changed_cell: BaseCell):
        self.set_dirty(True)
        if isinstance(changed_cell, CodeCell):
            self.on_cell_execution_requested(changed_cell)
        message = {"type": "cell_update", "cell_id": changed_cell.cell_id, "content": changed_cell.get_content()}
        self.collab_client.send_message(message)

    def on_refactor_requested(self, cell: CodeCell):
        """Handles the request to refactor a cell's code."""
        code_to_refactor = cell.get_content()
        if not code_to_refactor.strip(): return
        cell.output_area.setText("<i>Vibe Check in progress...</i>"); cell.output_area.show()
        system_prompt = settings_manager.get("prompts").get("vibe_check_refactor")
        chat_model = settings_manager.get("chat_model") or "ollama/llama3"
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": code_to_refactor}]
        self.run_ai_generation(cell, chat_model, messages, self.handle_refactor_result)

    def on_generate_action_requested(self, cell: CodeCell, action_type: str):
        """Handles requests to generate tests or docstrings."""
        code_to_process = cell.get_content()
        if not code_to_process.strip(): return
        cell.output_area.setText(f"<i>Generating {action_type}...</i>"); cell.output_area.show()
        prompt_key = f"generate_{action_type}"
        system_prompt = settings_manager.get("prompts").get(prompt_key)
        chat_model = settings_manager.get("chat_model") or "ollama/llama3"
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": code_to_process}]
        self.run_ai_generation(cell, chat_model, messages, lambda c, result: self.handle_generation_result(c, result, action_type))

    def run_ai_generation(self, cell: CodeCell, model_id: str, messages: list, result_handler):
        """Generic method to run an AI task in a background thread."""
        thread = AIGenerationThread(model_id, messages)
        thread.finished.connect(lambda result: result_handler(cell, result))
        thread.error.connect(lambda err: cell.output_area.setText(f"<font color='red'>{err}</font>"))
        thread.start()
        setattr(cell, f"_{id(thread)}", thread)

    def handle_refactor_result(self, cell: CodeCell, refactored_code: str):
        if not refactored_code.strip().startswith("[Error:"):
            cell.set_content(refactored_code)
            cell.output_area.setText("<i>Vibe Check complete. Code has been refactored.</i>")
        else:
            cell.output_area.setText(f"<font color='red'>{refactored_code}</font>")

    def handle_generation_result(self, cell: CodeCell, generated_content: str, action_type: str):
        if not generated_content.strip().startswith("[Error:"):
            if action_type == "tests":
                current_index = self.cell_order.index(cell.cell_id)
                self.add_cell('code', content=f"#| test\n{generated_content}", at_index=current_index + 1)
                cell.output_area.setText("<i>Test cell generated below.</i>")
            elif action_type == "docstring":
                # A simple implementation; a more robust one would use AST
                lines = cell.get_content().split('\n')
                if lines and 'def ' in lines[0]:
                    indent = ' ' * (lines[0].find('def') + 4)
                    docstring_lines = f'"""{generated_content}"""'.split('\n')
                    formatted_docstring = f"\n{indent}".join(docstring_lines)
                    new_code = f"{lines[0]}\n{indent}{formatted_docstring}\n" + "\n".join(lines[1:])
                    cell.set_content(new_code)
                    cell.output_area.setText("<i>Docstring inserted.</i>")
                else:
                    cell.output_area.setText("<i>Could not automatically insert docstring.</i>")
        else:
            cell.output_area.setText(f"<font color='red'>{generated_content}</font>")
    
    def delete_cell(self, cell_id: str, from_remote: bool = False):
        if cell_id in self.cells_by_id:
            cell_to_delete = self.cells_by_id.pop(cell_id)
            self.cell_order.remove(cell_id); cell_to_delete.deleteLater()
            self.rebuild_dependency_graph()
            if not from_remote:
                self.set_dirty(True)
                message = {"type": "delete_cell", "cell_id": cell_id}
                self.collab_client.send_message(message)

    def run_all_tests(self):
        self.execution_queue = [cell for cell_id in self.cell_order if isinstance((cell := self.cells_by_id.get(cell_id)), CodeCell) and cell.is_test_cell]
        if not self.execution_queue:
            reply = QMessageBox.question(self, "No Tests Found", "No test cells were found.\n\nWould you like to run all code cells instead?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes: self.run_all_cells()
            return
        self.execution_results = {}
        self._execute_next_in_queue(is_test_run=True)

    def _execute_next_in_queue(self, is_test_run=False):
        if not self.execution_queue:
            if is_test_run: self._show_test_summary()
            return
        cell_to_run = self.execution_queue.pop(0)
        cell_to_run.execution_finished.connect(lambda cid, res: self._on_queue_execution_finished(cid, res, is_test_run))
        cell_to_run.execute()

    def _on_queue_execution_finished(self, cell_id: str, result: dict, is_test_run: bool):
        cell = self.cells_by_id.get(cell_id)
        if not cell: return
        cell.execution_finished.disconnect()
        self.execution_results[cell_id] = result
        self._execute_next_in_queue(is_test_run)

    def _show_test_summary(self):
        passed_count = sum(1 for res in self.execution_results.values() if not any(item['type'] == 'error' for item in res.get('outputs', [])))
        total_count = len(self.execution_results)
        summary_message = f"Test run complete.\n\n{passed_count} / {total_count} tests passed."
        if passed_count == total_count: QMessageBox.information(self, "Test Results", summary_message)
        else: QMessageBox.warning(self, "Test Results", summary_message)

    def set_dirty(self, is_dirty: bool):
        if self._is_dirty != is_dirty: self._is_dirty = is_dirty; self.dirty_state_changed.emit(is_dirty)
    def is_dirty(self) -> bool: return self._is_dirty
    def to_dict(self) -> dict: return {"version": "1.0", "cells": [self.cells_by_id[cell_id].to_dict() for cell_id in self.cell_order]}
    def save_to_file(self, path: str):
        self.file_path = path
        try:
            with open(path, 'w', encoding='utf-8') as f: json.dump(self.to_dict(), f, indent=4)
            self.set_dirty(False)
        except IOError as e: QMessageBox.critical(self, "Save Error", f"Failed to save notebook: {e}")
    def load_from_file(self, path: str):
        self.file_path = path
        try:
            with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
            for i in range(self.cell_layout.count()): self.cell_layout.itemAt(i).widget().deleteLater()
            self.cells_by_id.clear(); self.cell_order.clear()
            for cell_data in data.get("cells", []): self.add_cell(cell_data['type'], cell_data['content'])
            self.set_dirty(False)
        except (IOError, json.JSONDecodeError) as e: QMessageBox.critical(self, "Load Error", f"Failed to load notebook: {e}")
    def export_to_script(self):
        if not self.file_path:
            QMessageBox.warning(self, "Save Notebook", "Please save the notebook before exporting.")
            return
        default_path = self.file_path.replace(".ipynb.json", ".py")
        save_path, _ = QFileDialog.getSaveFileName(self, "Export to Python Script", default_path, "Python Files (*.py)")
        if not save_path: return
        script_content = f"# --- Exported from {os.path.basename(self.file_path)} ---\n\n"
        for cell_id in self.cell_order:
            cell = self.cells_by_id.get(cell_id)
            if isinstance(cell, CodeCell) and not cell.is_test_cell:
                script_content += cell.get_content() + "\n\n# --------\n\n"
        try:
            with open(save_path, 'w', encoding='utf-8') as f: f.write(script_content)
            QMessageBox.information(self, "Export Successful", f"Notebook exported to:\n{save_path}")
        except IOError as e: QMessageBox.critical(self, "Export Error", f"Failed to export script: {e}")
    def on_collab_status_changed(self, status: str): self.collaboration_status_updated.emit(status)
    def on_cell_content_changed(self, changed_cell: BaseCell):
        self.set_dirty(True)
        if isinstance(changed_cell, CodeCell):
            self.on_cell_execution_requested(changed_cell)
        message = {"type": "cell_update", "cell_id": changed_cell.cell_id, "content": changed_cell.get_content()}
        self.collab_client.send_message(message)
    def on_remote_change(self, data: dict):
        msg_type = data.get("type"); cell_id = data.get("cell_id")
        if msg_type == "cell_update":
            if cell_id in self.cells_by_id: self.cells_by_id[cell_id].set_content(data.get("content"), from_remote=True)
        elif msg_type == "add_cell":
            self.add_cell(data.get("cell_type"), data.get("content"), cell_id, from_remote=True)
        elif msg_type == "delete_cell":
            if cell_id in self.cells_by_id: self.delete_cell(cell_id, from_remote=True)
    def on_remote_user_activity(self, data: dict):
        if data.get("type") == "cursor_update":
            cell_id = data.get("cell_id")
            if cell_id in self.cells_by_id:
                self.cells_by_id[cell_id].update_remote_cursor(data['client_id'], data['cursor_pos'], data['selection_end'])
    def on_local_cursor_activity(self, cell_id: str, cursor_pos: int, selection_end: int):
        self.collab_client.send_cursor_update(cell_id, cursor_pos, selection_end)
    def closeEvent(self, event):
        self.collab_client.stop(); kernel_manager_service.shutdown_kernel(self.notebook_id)
        super().closeEvent(event)
    def apply_styles(self):
        self.setStyleSheet("""
            QFrame { border: 1px solid #2c3e50; border-radius: 4px; }
            QToolBar { border: none; }
            CodeCell { background-color: #1c2833; }
        """)
