# main_app.py
# © 2025 Colt McVey
# The main entry point for the AI-Native Development Environment.

import sys
import os
import asyncio
import logging
import traceback

# --- Dependency Check & Setup ---
# This must be the very first Qt-related action.
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

try:
    from PySide6.QtWidgets import QMessageBox, QLabel
    import markdown2
    import jupyter_client
    from jupyter_client.kernelspec import NoSuchKernel
    import networkx
    import pygments
except ImportError as e:
    error_box = QMessageBox()
    error_box.setIcon(QMessageBox.Icon.Critical)
    missing_module = e.name
    error_box.setText("Missing Required Dependency")
    error_box.setInformativeText(f"Please install '{missing_module}' via pip, then restart.")
    error_box.exec()
    sys.exit(1)

from PySide6.QtWidgets import (
    QMainWindow, QSplashScreen, QTabWidget, QVBoxLayout,
    QWidget, QStatusBar, QMenuBar, QMenu, QDockWidget,
    QFileDialog, QTextEdit
)
from PySide6.QtGui import QPixmap, QFont, QAction, QIcon, QPalette, QColor, QPainter
from PySide6.QtCore import Qt, QTimer, QSize, QRect

# --- Import Custom Widgets and Services ---
try:
    import config
    from arena_ui import ArenaWidget
    from scaffolder import ScaffolderWidget
    from notebook import NotebookWidget, CodeCell
    from visual_canvas import VisualCanvasWidget
    from leaderboard import LeaderboardWidget
    from chat_panel import ChatPanel
    from kernel_manager import kernel_manager_service
    from settings_dialog import SettingsDialog
    from theme_manager import theme_manager
    from about_dialog import AboutDialog
    from ui_utils import create_icon_from_svg, SVG_ICONS
    from file_browser import FileBrowserWidget
    from terminal_widget import TerminalWidget
    from debugger_widget import DebuggerWidget
    from llm_interface import InferenceEngine
except ImportError as e:
    logging.critical(f"Failed to import a required application module: {e.name}. Please ensure all .py files are in the same directory.")
    QMessageBox.critical(None, "Module Not Found", f"A required file is missing: {e.name}.py\nPlease ensure all application files are present and try again.")
    sys.exit(1)


class MainWindow(QMainWindow):
    """
    The main window of the application, hosting the tabbed workspace
    and all major components.
    """
    def __init__(self, all_models: list):
        super().__init__()
        logging.info("Initializing MainWindow...")
        self.setWindowTitle(config.APP_NAME)
        self.setWindowIcon(create_icon_from_svg(SVG_ICONS["app_logo"]))
        self.setGeometry(100, 100, 1800, 1000)
        self.notebook_tabs = {}
        self.all_models = all_models
        
        self.setup_chat_panel()
        self.setup_file_browser()
        self.setup_bottom_panels()
        self.setup_ui()
        self.create_menus()
        logging.info("MainWindow initialization complete.")

    def setup_ui(self):
        logging.info("Setting up main UI...")
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.collab_status_label = QLabel("Collaboration: Disconnected")
        self.status_bar.addPermanentWidget(self.collab_status_label)
        self.status_bar.showMessage("Ready.")
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.on_tab_close_requested)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        self.layout.addWidget(self.tab_widget)
        
        logging.info("Adding tabs...")
        self.new_notebook("Initial Notebook")
        canvas_widget = VisualCanvasWidget()
        canvas_widget.open_notebook_for_node.connect(self.open_or_focus_notebook)
        self.add_tab(canvas_widget, "Visual Canvas", "canvas.png")
        
        arena_widget = ArenaWidget()
        arena_widget.populate_models(self.all_models)
        self.add_tab(arena_widget, "Model Arena", "arena.png")
        
        self.add_tab(LeaderboardWidget(), "Leaderboard", "leaderboard.png")
        self.add_tab(ScaffolderWidget(), "App Factory", "factory.png")
        
        logging.info("Main UI setup complete.")

    def setup_chat_panel(self):
        logging.info("Setting up chat panel...")
        self.chat_dock = QDockWidget("AI Chat", self)
        self.chat_panel = ChatPanel()
        self.chat_panel.insert_code_in_notebook.connect(self.on_insert_code_requested)
        self.chat_dock.setWidget(self.chat_panel)
        self.chat_dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.chat_dock)
        logging.info("Chat panel setup complete.")
        
    def setup_file_browser(self):
        logging.info("Setting up file browser...")
        self.file_browser_dock = QDockWidget("Context Files", self)
        self.file_browser = FileBrowserWidget()
        self.file_browser.context_files_changed.connect(self.chat_panel.set_file_context)
        self.file_browser_dock.setWidget(self.file_browser)
        self.file_browser_dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.file_browser_dock)
        logging.info("File browser setup complete.")

    def setup_bottom_panels(self):
        logging.info("Setting up bottom panels...")
        
        self.bottom_dock_tabs = QTabWidget()
        self.bottom_dock_tabs.setTabsClosable(False)

        self.terminal_panel = TerminalWidget()
        self.debugger_panel = DebuggerWidget()

        self.bottom_dock_tabs.addTab(self.terminal_panel, "Terminal")
        self.bottom_dock_tabs.addTab(self.debugger_panel, "Debugger")
        
        self.bottom_dock = QDockWidget("Console", self)
        self.bottom_dock.setWidget(self.bottom_dock_tabs)
        self.bottom_dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.bottom_dock)
        
        logging.info("Bottom panels setup complete.")

    def on_insert_code_requested(self, code: str):
        """Handles the request from the chat panel to insert code."""
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, NotebookWidget):
            current_widget.add_cell('code', content=code)
            self.status_bar.showMessage("Code inserted into the active notebook.", 3000)
        else:
            QMessageBox.warning(self, "No Active Notebook", "Please open or select a notebook tab to insert code.")

    def create_menus(self):
        logging.info("Creating menus...")
        menu_bar = self.menuBar()
        
        file_menu = menu_bar.addMenu("&File")
        new_action = QAction("New Notebook", self); new_action.triggered.connect(self.new_notebook); file_menu.addAction(new_action)
        open_action = QAction("Open Notebook...", self); open_action.triggered.connect(self.open_notebook_file); file_menu.addAction(open_action)
        file_menu.addSeparator()
        save_action = QAction("Save", self); save_action.triggered.connect(self.save_current_notebook); file_menu.addAction(save_action)
        save_as_action = QAction("Save As...", self); save_as_action.triggered.connect(self.save_current_notebook_as); file_menu.addAction(save_as_action)
        file_menu.addSeparator()
        settings_action = QAction("Settings...", self); settings_action.triggered.connect(self.open_settings); file_menu.addAction(settings_action)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self); exit_action.triggered.connect(self.close); file_menu.addAction(exit_action)
        
        view_menu = menu_bar.addMenu("&View")
        toggle_chat_action = self.chat_dock.toggleViewAction(); toggle_chat_action.setText("Toggle Chat Panel"); view_menu.addAction(toggle_chat_action)
        toggle_files_action = self.file_browser_dock.toggleViewAction(); toggle_files_action.setText("Toggle File Browser"); view_menu.addAction(toggle_files_action)
        toggle_bottom_panel_action = self.bottom_dock.toggleViewAction(); toggle_bottom_panel_action.setText("Toggle Console Panel"); view_menu.addAction(toggle_bottom_panel_action)
        view_menu.addSeparator()
        
        open_canvas_action = QAction("Open Visual Canvas", self)
        open_canvas_action.triggered.connect(lambda: self._open_or_focus_tab(VisualCanvasWidget, "Visual Canvas", "canvas.png"))
        view_menu.addAction(open_canvas_action)

        open_arena_action = QAction("Open Model Arena", self)
        open_arena_action.triggered.connect(lambda: self._open_or_focus_tab(ArenaWidget, "Model Arena", "arena.png"))
        view_menu.addAction(open_arena_action)

        open_leaderboard_action = QAction("Open Leaderboard", self)
        open_leaderboard_action.triggered.connect(lambda: self._open_or_focus_tab(LeaderboardWidget, "Leaderboard", "leaderboard.png"))
        view_menu.addAction(open_leaderboard_action)

        open_factory_action = QAction("Open App Factory", self)
        open_factory_action.triggered.connect(lambda: self._open_or_focus_tab(ScaffolderWidget, "App Factory", "factory.png"))
        view_menu.addAction(open_factory_action)

        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction(f"About {config.APP_NAME}", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        
        logging.info("Menu creation complete.")

    def _open_or_focus_tab(self, widget_class, title: str, icon_path: str):
        """A generic helper to open a new tab or focus an existing one."""
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, widget_class):
                self.tab_widget.setCurrentIndex(i)
                return
        
        if widget_class == VisualCanvasWidget:
            new_widget = VisualCanvasWidget()
            new_widget.open_notebook_for_node.connect(self.open_or_focus_notebook)
        else:
            new_widget = widget_class()
            if isinstance(new_widget, ArenaWidget):
                new_widget.populate_models(self.all_models)
            
        self.add_tab(new_widget, title, icon_path)

    def show_about_dialog(self):
        """Creates and shows the About dialog."""
        dialog = AboutDialog(self)
        dialog.exec()

    def open_settings(self):
        """Opens the settings dialog, passing the cached list of models."""
        dialog = SettingsDialog(self.all_models, self)
        if dialog.exec():
            QApplication.instance().setStyleSheet(theme_manager.get_active_theme_stylesheet())
            QMessageBox.information(self, "Settings Applied", "Theme has been updated. Other settings may require a restart.")

    def on_tab_changed(self):
        self.update_chat_context()
        self.update_collab_status_for_current_tab()

    def update_collab_status_for_current_tab(self):
        widget = self.tab_widget.currentWidget()
        if isinstance(widget, NotebookWidget):
            self.on_notebook_collab_status_updated(widget.collab_client.connection_status_changed.emit)
        else:
            self.collab_status_label.setText("")

    def on_notebook_collab_status_updated(self, status: str):
        if self.sender() and self.sender().parent() == self.tab_widget.currentWidget():
            self.collab_status_label.setText(f"Collaboration: {status}")

    def update_chat_context(self):
        if not hasattr(self, 'chat_panel'): return
        current_widget = self.tab_widget.currentWidget()
        context = ""
        file_path = None
        
        if isinstance(current_widget, NotebookWidget):
            file_path = current_widget.file_path
            focused_cell = current_widget.focusWidget()
            if isinstance(focused_cell, QTextEdit):
                cursor = focused_cell.textCursor()
                context = cursor.selectedText() or focused_cell.toPlainText()
        
        self.chat_panel.set_editor_context(context, file_path)

    def add_tab(self, widget, title, icon_path=None):
        if isinstance(widget, NotebookWidget):
            widget.dirty_state_changed.connect(self.on_notebook_dirty_state_changed)
            widget.collaboration_status_updated.connect(self.on_notebook_collab_status_updated)
            for cell in widget.cells_by_id.values():
                if isinstance(cell, CodeCell):
                    cell.editor.selectionChanged.connect(self.update_chat_context)
        icon = QIcon(icon_path) if icon_path and os.path.exists(icon_path) else QIcon()
        index = self.tab_widget.addTab(widget, icon, title)
        self.tab_widget.setCurrentIndex(index)
        return index

    def on_tab_close_requested(self, index):
        """Handles the request to close a single tab."""
        self._close_tab_at_index(index)

    def _close_tab_at_index(self, index, force_close=False):
        """Internal logic to close a tab, returns True if successful."""
        widget = self.tab_widget.widget(index)
        if isinstance(widget, NotebookWidget) and widget.is_dirty() and not force_close:
            self.tab_widget.setCurrentIndex(index)
            reply = QMessageBox.question(self, 'Unsaved Changes', "Save changes before closing?",
                                         QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                self.save_current_notebook()
                if widget.is_dirty(): return False
            elif reply == QMessageBox.StandardButton.Cancel:
                return False
        
        if isinstance(widget, NotebookWidget):
            if widget.notebook_id in self.notebook_tabs: del self.notebook_tabs[widget.notebook_id]
            widget.closeEvent(None)
        if widget: widget.deleteLater()
        self.tab_widget.removeTab(index)
        return True

    def new_notebook(self, name: str = None):
        notebook_widget = NotebookWidget()
        if name is None: name = "Untitled Notebook"
        index = self.add_tab(notebook_widget, f"{name} *", "notebook.png")
        self.notebook_tabs[notebook_widget.notebook_id] = index

    def open_notebook_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Notebook", "", "Notebook Files (*.ipynb.json)")
        if path:
            notebook_widget = NotebookWidget(file_path=path)
            index = self.add_tab(notebook_widget, os.path.basename(path), "notebook.png")
            self.notebook_tabs[notebook_widget.notebook_id] = index

    def save_current_notebook(self):
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, NotebookWidget):
            if current_widget.file_path:
                current_widget.save_to_file(current_widget.file_path)
            else:
                self.save_current_notebook_as()

    def save_current_notebook_as(self):
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, NotebookWidget):
            path, _ = QFileDialog.getSaveFileName(self, "Save Notebook As", "", "Notebook Files (*.ipynb.json)")
            if path:
                current_widget.save_to_file(path)
                self.tab_widget.setTabText(self.tab_widget.currentIndex(), os.path.basename(path))

    def on_notebook_dirty_state_changed(self, is_dirty):
        sender_widget = self.sender()
        for i in range(self.tab_widget.count()):
            if self.tab_widget.widget(i) == sender_widget:
                current_text = self.tab_widget.tabText(i).removesuffix(" *")
                self.tab_widget.setTabText(i, f"{current_text} *" if is_dirty else current_text)
                break

    def open_or_focus_notebook(self, notebook_id: str, node_name: str):
        if notebook_id in self.notebook_tabs:
            self.tab_widget.setCurrentIndex(self.notebook_tabs[notebook_id])
            return
        notebook_widget = NotebookWidget(notebook_id=notebook_id)
        index = self.add_tab(notebook_widget, f"Node: {node_name}", "notebook.png")
        self.notebook_tabs[notebook_widget.notebook_id] = index

    def closeEvent(self, event):
        logging.info("Close event triggered. Checking for unsaved changes...")
        while self.tab_widget.count() > 0:
            if not self._close_tab_at_index(0):
                logging.warning("Tab close was cancelled by user. Aborting main window close.")
                event.ignore()
                return
        logging.info("All tabs closed successfully. Accepting close event.")
        event.accept()

async def main_async(app):
    """The main async entry point for the application."""
    logging.info("Application starting...")
    
    app.setStyleSheet(theme_manager.get_active_theme_stylesheet())
    
    app.setFont(QFont("Inter", 10))
    app.aboutToQuit.connect(kernel_manager_service.shutdown_all)

    splash_pixmap = QPixmap(400, 250)
    splash_pixmap.fill(QColor("#1a2533"))
    painter = QPainter(splash_pixmap)
    logo_icon = create_icon_from_svg(SVG_ICONS["app_logo"], QSize(128, 128))
    logo_pixmap = logo_icon.pixmap(QSize(128, 128))
    painter.drawPixmap(136, 20, logo_pixmap)
    
    font = QFont("Inter", 16, QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor("#ecf0f1"))
    painter.drawText(QRect(0, 150, 400, 40), Qt.AlignmentFlag.AlignCenter, config.APP_NAME)
    
    font.setPointSize(10)
    font.setItalic(True)
    painter.setFont(font)
    painter.drawText(QRect(0, 180, 400, 30), Qt.AlignmentFlag.AlignCenter, f'"{config.APP_SLOGAN}"')
    painter.end()

    splash = QSplashScreen(splash_pixmap)
    splash.show()
    
    main_win = None
    try:
        logging.info("Creating MainWindow instance...")
        
        # --- Pre-fetch Models Before Creating the Main Window ---
        logging.info("Asynchronously loading models...")
        engine = InferenceEngine()
        all_models_dict = await engine.get_all_models()
        all_models_list = [f"{p}/{m}" for p, models in all_models_dict.items() for m in models]
        logging.info(f"Model loading complete. Found: {all_models_list}")

        main_win = MainWindow(all_models_list)
        
        main_win.show()
        splash.finish(main_win)
        logging.info("MainWindow shown, starting event loop.")
    except Exception as e:
        logging.critical(f"An unexpected error occurred during startup: {e}", exc_info=True)
        QMessageBox.critical(None, "Application Failed to Start", f"An unexpected error occurred:\n\n{e}\n\n{traceback.format_exc()}")
        splash.close(); sys.exit(1)

    while main_win and main_win.isVisible():
        app.processEvents()
        await asyncio.sleep(0.01)
    
    logging.info("Main window closed. Exiting application.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    print(f"--- {config.APP_NAME} ---")
    print("NOTE: For real-time collaboration, start the server with: python collaboration_server.py")
    print("-----------------------------------------")
    try:
        # The app instance is now passed to the async main function
        asyncio.run(main_async(app))
    except KeyboardInterrupt:
        print("Application interrupted by user.")
    except Exception as e:
        logging.critical(f"Top-level application error: {e}", exc_info=True)