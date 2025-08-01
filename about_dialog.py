# about_dialog.py
# © 2025 Colt McVey
# The "About" dialog for the application.

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

# Import app configuration and UI utilities
import config
from ui_utils import create_icon_from_svg, SVG_ICONS

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {config.APP_NAME}")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # --- Logo ---
        logo_label = QLabel()
        logo_icon = create_icon_from_svg(SVG_ICONS["app_logo"], QSize(128, 128))
        logo_label.setPixmap(logo_icon.pixmap(QSize(128, 128)))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # --- App Name and Motto ---
        name_label = QLabel(config.APP_NAME)
        name_label.setFont(QFont("Inter", 24, QFont.Weight.Bold))
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        motto_label = QLabel(config.APP_MOTTO)
        motto_label.setFont(QFont("Inter", 10, QFont.Weight.Normal, italic=True))
        motto_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        slogan_label = QLabel(f'"{config.APP_SLOGAN}"')
        slogan_label.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        slogan_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slogan_label.setWordWrap(True)

        # --- Version and Copyright ---
        version_label = QLabel(f"Version: {config.APP_VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        copyright_label = QLabel(config.APP_COPYRIGHT)
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # --- OK Button ---
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)

        layout.addWidget(logo_label)
        layout.addWidget(name_label)
        layout.addWidget(motto_label)
        layout.addWidget(slogan_label)
        layout.addStretch()
        layout.addWidget(version_label)
        layout.addWidget(copyright_label)
        layout.addWidget(button_box)
