# theme_manager.py
# © 2025 Colt McVey
# Manages loading, applying, and generating stylesheets from theme files.

import json
import os
import logging
from settings_manager import settings_manager
from data_manager import get_app_data_dir

# The themes directory is now located in the user's app data directory.
THEMES_DIR = get_app_data_dir() / "themes"

# Define a list of default themes that will be created if their files don't exist.
DEFAULT_THEMES = [
    {
        "name": "Bright Blue",
        "description": "A bright, accessible blue and charcoal theme.",
        "colors": {
            "background_base": "#1a2533",
            "background_light": "#1c2833",
            "surface": "#2c3e50",
            "primary": "#007BFF",
            "primary_hover": "#3395ff",
            "primary_pressed": "#0056b3",
            "text_main": "#F5F5F5",
            "text_dim": "#bdc3c7",
            "error": "#e74c3c",
            "button_text": "#ffffff",
            "user_bubble": "#2c3e50",
            "ai_bubble": "#1c2833",
            "code_header": "#2c3e50",
            "code_keyword": "#569cd6",
            "code_string": "#ce9178",
            "code_comment": "#6a9955",
            "code_number": "#b5cea8"
        },
        "fonts": {
            "main": "Inter",
            "monospace": "Courier New"
        }
    },
    {
        "name": "Classic White",
        "description": "A traditional light theme with black text and blue accents.",
        "colors": {
            "background_base": "#FFFFFF",
            "background_light": "#F8F9FA",
            "surface": "#E9ECEF",
            "primary": "#007BFF",
            "primary_hover": "#4DA3FF",
            "primary_pressed": "#0056B3",
            "text_main": "#212529",
            "text_dim": "#6C757D",
            "error": "#DC3545",
            "button_text": "#ffffff",
            "user_bubble": "#E9ECEF",
            "ai_bubble": "#F8F9FA",
            "code_header": "#E9ECEF",
            "code_keyword": "#005cc5",
            "code_string": "#d73a49",
            "code_comment": "#6a737d",
            "code_number": "#005cc5"
        },
        "fonts": {
            "main": "Inter",
            "monospace": "Courier New"
        }
    },
    {
        "name": "Pastel Pink",
        "description": "A soft, colorful theme with pink and purple pastels.",
        "colors": {
            "background_base": "#FFF0F5",
            "background_light": "#FFFFFF",
            "surface": "#FADADD",
            "primary": "#FF69B4",
            "primary_hover": "#FF85C1",
            "primary_pressed": "#D45095",
            "text_main": "#5D4037",
            "text_dim": "#8D6E63",
            "error": "#E53935",
            "button_text": "#ffffff",
            "user_bubble": "#FADADD",
            "ai_bubble": "#FFFFFF",
            "code_header": "#FADADD",
            "code_keyword": "#d0368a",
            "code_string": "#c3e88d",
            "code_comment": "#b0a4e3",
            "code_number": "#82aaff"
        },
        "fonts": {
            "main": "Inter",
            "monospace": "Courier New"
        }
    },
    {
        "name": "Neon Blue",
        "description": "A high-contrast theme with neon blue accents.",
        "colors": {
            "background_base": "#0a0f14",
            "background_light": "#101820",
            "surface": "#1a2a3a",
            "primary": "#00d9ff",
            "primary_hover": "#66eaff",
            "primary_pressed": "#00b8d9",
            "text_main": "#e0e0e0",
            "text_dim": "#a0a0a0",
            "error": "#ff4d4d",
            "button_text": "#0a0f14",
            "user_bubble": "#1a2a3a",
            "ai_bubble": "#101820",
            "code_header": "#1a2a3a",
            "code_keyword": "#569cd6",
            "code_string": "#ce9178",
            "code_comment": "#6a9955",
            "code_number": "#b5cea8"
        },
        "fonts": {
            "main": "Inter",
            "monospace": "Courier New"
        }
    },
    {
        "name": "Patriotic",
        "description": "A theme using red, white, and blue.",
        "colors": {
            "background_base": "#f0f0f0",
            "background_light": "#ffffff",
            "surface": "#e0e0e0",
            "primary": "#b31942",
            "primary_hover": "#d91f4e",
            "primary_pressed": "#8c1334",
            "text_main": "#0a3161",
            "text_dim": "#50698c",
            "error": "#b31942",
            "button_text": "#ffffff",
            "user_bubble": "#e0e0e0",
            "ai_bubble": "#ffffff",
            "code_header": "#e0e0e0",
            "code_keyword": "#0a3161",
            "code_string": "#b31942",
            "code_comment": "#6a737d",
            "code_number": "#0a3161"
        },
        "fonts": {
            "main": "Inter",
            "monospace": "Courier New"
        }
    },
    {
        "name": "Obsidian",
        "description": "A super dark theme with shades of black and gray.",
        "colors": {
            "background_base": "#000000",
            "background_light": "#121212",
            "surface": "#1E1E1E",
            "primary": "#BB86FC",
            "primary_hover": "#D0A0FF",
            "primary_pressed": "#A75EFA",
            "text_main": "#E0E0E0",
            "text_dim": "#A0A0A0",
            "error": "#CF6679",
            "button_text": "#000000",
            "user_bubble": "#1E1E1E",
            "ai_bubble": "#121212",
            "code_header": "#1E1E1E",
            "code_keyword": "#c586c0",
            "code_string": "#ce9178",
            "code_comment": "#6a9955",
            "code_number": "#b5cea8"
        },
        "fonts": {
            "main": "Inter",
            "monospace": "Courier New"
        }
    },
    {
        "name": "Midnight Copper",
        "description": "A dark theme with black and copper/orange tones.",
        "colors": {
            "background_base": "#121212",
            "background_light": "#1E1E1E",
            "surface": "#2A2A2A",
            "primary": "#D97706",
            "primary_hover": "#F59E0B",
            "primary_pressed": "#B45309",
            "text_main": "#FDE68A",
            "text_dim": "#9CA3AF",
            "error": "#EF4444",
            "button_text": "#FFFFFF",
            "user_bubble": "#2A2A2A",
            "ai_bubble": "#1E1E1E",
            "code_header": "#2A2A2A",
            "code_keyword": "#f97316",
            "code_string": "#fde047",
            "code_comment": "#a3a3a3",
            "code_number": "#f59e0b"
        },
        "fonts": {
            "main": "Inter",
            "monospace": "Courier New"
        }
    }
]

class ThemeManager:
    def __init__(self):
        self.themes = {}
        THEMES_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_default_themes_exist()
        self.load_themes()

    def _ensure_default_themes_exist(self):
        """Checks for default theme files and creates them if they are missing."""
        for theme_data in DEFAULT_THEMES:
            theme_name = theme_data['name']
            file_path = THEMES_DIR / f"{theme_name.replace(' ', '_').lower()}.json"
            if not os.path.exists(file_path):
                self.save_theme(theme_data)

    def load_themes(self):
        """Loads all .json theme files from the themes directory."""
        self.themes = {}
        for filename in os.listdir(THEMES_DIR):
            if filename.endswith(".json"):
                try:
                    with open(THEMES_DIR / filename, 'r') as f:
                        theme_data = json.load(f)
                        self.themes[theme_data['name']] = theme_data
                except (json.JSONDecodeError, KeyError, IOError) as e:
                    logging.warning(f"Could not load theme file '{filename}': {e}")
        
        if not self.themes:
            logging.error("No themes could be loaded.")

    def get_theme_names(self) -> list[str]:
        """Returns a list of available theme names."""
        return sorted(list(self.themes.keys()))

    def get_theme_data(self, name: str) -> dict:
        """Gets the data for a specific theme by name."""
        # Fallback to the first default theme if the requested one isn't found
        return self.themes.get(name, DEFAULT_THEMES[0])

    def save_theme(self, theme_data: dict):
        """Saves a theme's data to a file."""
        theme_name = theme_data['name']
        file_path = THEMES_DIR / f"{theme_name.replace(' ', '_').lower()}.json"
        try:
            with open(file_path, 'w') as f:
                json.dump(theme_data, f, indent=4)
            self.themes[theme_name] = theme_data
        except IOError as e:
            logging.error(f"Failed to save theme '{theme_name}': {e}")

    def get_active_theme_stylesheet(self) -> str:
        """Generates a full Qt stylesheet from the active theme."""
        active_theme_name = settings_manager.get("active_theme")
        theme_data = self.get_theme_data(active_theme_name)
        
        c = theme_data['colors']
        f = theme_data['fonts']
        
        # --- Robust Stylesheet Generation with Fallbacks ---
        return f"""
            QWidget {{
                background-color: {c.get('background_base', '#1a2533')};
                color: {c.get('text_main', '#ecf0f1')};
                font-family: "{f.get('main', 'Inter')}", sans-serif;
            }}
            QMainWindow, QDockWidget {{ background-color: {c.get('background_base', '#1a2533')}; }}
            QDockWidget::title {{ background-color: {c.get('surface', '#2c3e50')}; color: {c.get('text_main', '#ecf0f1')}; padding: 5px; }}
            QMenuBar {{ background-color: {c.get('surface', '#2c3e50')}; color: {c.get('text_main', '#ecf0f1')}; }}
            QMenuBar::item:selected {{ background-color: {c.get('primary_hover', '#5dade2')}; }}
            QMenu {{ background-color: {c.get('surface', '#2c3e50')}; color: {c.get('text_main', '#ecf0f1')}; border: 1px solid {c.get('background_base', '#1a2533')}; }}
            QMenu::item:selected {{ background-color: {c.get('primary_hover', '#5dade2')}; }}
            QTabWidget::pane {{ border-top: 2px solid {c.get('surface', '#2c3e50')}; }}
            QTabBar::tab {{ background: {c.get('surface', '#2c3e50')}; color: {c.get('text_main', '#ecf0f1')}; padding: 10px; border: 1px solid {c.get('background_base', '#1a2533')}; border-bottom: none; }}
            QTabBar::tab:selected, QTabBar::tab:hover {{ background: {c.get('primary', '#3498db')}; }}
            QPushButton {{ background-color: {c.get('primary', '#3498db')}; color: {c.get('button_text', '#ffffff')}; border: none; border-radius: 5px; padding: 8px; font-weight: bold; }}
            QPushButton:hover {{ background-color: {c.get('primary_hover', '#5dade2')}; }}
            QPushButton:pressed {{ background-color: {c.get('primary_pressed', '#2e86c1')}; }}
            QPushButton:disabled {{ background-color: {c.get('surface', '#2c3e50')}; color: #808080; }}
            QLineEdit, QTextEdit, QSpinBox, QComboBox {{ background-color: {c.get('background_light', '#1c2833')}; color: {c.get('text_main', '#ecf0f1')}; border: 1px solid {c.get('surface', '#2c3e50')}; border-radius: 5px; padding: 5px; }}
            QTextEdit[font-family="{f.get('monospace', 'Courier New')}"] {{ font-family: "{f.get('monospace', 'Courier New')}"; }}
            QComboBox::drop-down {{ border: none; }}
            QGroupBox {{ color: {c.get('text_main', '#e0e0e0')}; font-weight: bold; border: 1px solid {c.get('surface', '#2c3e50')}; border-radius: 8px; margin-top: 10px; }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; background-color: {c.get('background_base', '#1a2533')}; }}
            QDialog {{ background-color: {c.get('background_base', '#1a2533')}; }}
            QListWidget, QTreeWidget, QTableWidget {{ background-color: {c.get('background_light', '#1c2833')}; border: 1px solid {c.get('surface', '#2c3e50')}; }}
            QHeaderView::section {{ background-color: {c.get('surface', '#2c3e50')}; padding: 4px; border: 1px solid {c.get('background_base', '#1a2533')}; font-weight: bold; }}

            /* --- Chat Panel Specific Styles --- */
            QTextBrowser#userMessageBubble {{
                background-color: {c.get('user_bubble', c.get('surface'))};
                color: {c.get('text_main')};
                padding: 8px;
                border-radius: 10px;
                border: none;
            }}
            AIMessageBubble {{
                background-color: {c.get('ai_bubble', c.get('background_light'))};
                padding: 10px;
                border-radius: 10px;
                color: {c.get('text_main')};
            }}
            AIMessageBubble QTextBrowser {{ background-color: transparent; border: none; color: {c.get('text_main')}; }}
            CodeBlockWidget {{ border-radius: 8px; background-color: {c.get('background_light')}; }}
            CodeBlockWidget > QFrame {{ background-color: {c.get('code_header', c.get('surface'))}; border-top-left-radius: 8px; border-top-right-radius: 8px; }}
            CodeBlockWidget QLabel {{ color: {c.get('text_dim')}; font-family: sans-serif; }}
            CodeBlockWidget QTextBrowser {{ background-color: transparent; border: none; padding: 10px; font-family: "{f.get('monospace')}"; }}

            /* --- Enhanced Pygments Styles --- */
            .codehilite .k {{ color: {c.get('code_keyword', '#569cd6')}; font-weight: bold }}
            .codehilite .s, .codehilite .s1, .codehilite .s2 {{ color: {c.get('code_string', '#ce9178')} }}
            .codehilite .c, .codehilite .c1 {{ color: {c.get('code_comment', '#6a9955')} }}
            .codehilite .m, .codehilite .mi {{ color: {c.get('code_number', '#b5cea8')} }}
        """

# Global instance
theme_manager = ThemeManager()