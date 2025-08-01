# data_manager.py
# © 2025 Colt McVey
# Manages the application's data directory for user-specific files.

import os
from pathlib import Path
import sys

def get_app_data_dir() -> Path:
    """
    Gets the appropriate, writable directory for application data.
    """
    app_name = "crap_ai"

    if getattr(sys, 'frozen', False):
        if sys.platform == "win32":
            app_data_path = Path(os.getenv("APPDATA")) / app_name
        elif sys.platform == "darwin":
            app_data_path = Path.home() / "Library" / "Application Support" / app_name
        else:
            app_data_path = Path.home() / ".config" / app_name
    else:
        app_data_path = Path(".") / "app_data"

    app_data_path.mkdir(parents=True, exist_ok=True)
    return app_data_path
