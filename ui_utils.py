# ui_utils.py
# © 2025 Colt McVey
# Shared utility functions and constants for the UI.

from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtCore import Qt, QSize
from PySide6.QtSvg import QSvgRenderer

# Central repository for all SVG icons used in the application.
SVG_ICONS = {
    "app_logo": """<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24"><path fill="#795548" d="M12 2c-4.42 0-8 3.58-8 8c0 2.36.96 4.59 2.75 6.09c.28.23.53.49.75.77c.2.25.39.51.56.78c.21.32.4.67.56.97c.23.45.4.82.5 1.19h8.8c.1-.37.27-.74.5-1.19c.16-.3.35-.65.56-.97c.17-.27.36-.53.56-.78c.22-.28.47-.54.75-.77C19.04 14.59 20 12.36 20 10c0-4.42-3.58-8-8-8z"/><path fill="#000000" d="M8 11h8v2H8z"/><path fill="#FFFFFF" d="M9.5 12a.5.5 0 0 1-.5-.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5zm-2-2a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 1 0v-3a.5.5 0 0 0-.5-.5zm10 0a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 1 0v-3a.5.5 0 0 0-.5-.5z"/></svg>""",
    "notebook": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 6h4"/><path d="M2 12h4"/><path d="M2 18h4"/><rect x="10" y="4" width="12" height="16" rx="2"/></svg>""",
    "canvas": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="8" y1="12" x2="16" y2="12"></line><line x1="12" y1="8" x2="12" y2="16"></line></svg>""",
    "add_code": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ecf0f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2l4 4-9 9H5v-4l9-9z"/><path d="M5 19h14"/></svg>""",
    "add_md": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ecf0f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h16M4 12h16M4 18h16"/></svg>""",
    "run_cell": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ecf0f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>""",
    "run_all": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ecf0f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 7-7 7 7"/><path d="m5 19 7-7 7 7"/></svg>""",
    "run_tests": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ecf0f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>""",
    "export": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ecf0f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>""",
    "delete": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#e74c3c" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>""",
    "upload": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ecf0f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>"""
}

def create_icon_from_svg(svg_string: str, size=None) -> QIcon:
    """Creates a QIcon from a raw SVG string, optionally resizing it."""
    renderer = QSvgRenderer(svg_string.encode('utf-8'))
    if size is None:
        size = renderer.defaultSize()
    
    pixmap = QPixmap(size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)