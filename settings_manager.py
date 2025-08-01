# settings_manager.py
# © 2025 Colt McVey
# A centralized manager for application settings.

import json
import os
import logging
from data_manager import get_app_data_dir

SETTINGS_FILE = get_app_data_dir() / "app_settings.json"

# Default prompts now include prompts for test and docstring generation.
DEFAULT_PROMPTS = {
    "app_factory_plan": """
You are a world-class principal software architect...
""",
    "app_factory_code": """
You are a world-class principal software engineer...
""",
    "ai_chat_system": """
You are an expert AI programming assistant...
""",
    "ai_chat_project_aware": """
You are an expert AI programming assistant...
""",
    "vibe_check_refactor": """
You are a world-class principal software engineer acting as a code reviewer. Your name is CRAP.
You are reviewing a piece of code written by a junior developer. Your task is to analyze the provided code and rewrite it to be more efficient, readable, and idiomatic, adhering to the highest standards of software engineering.

**CRITICAL INSTRUCTIONS:**
1.  **Analyze and Refactor:** Carefully analyze the user's code for any logical errors, performance bottlenecks, code smells, or deviations from best practices.
2.  **Return Only Code:** Your entire response must be **only the refactored, complete, and runnable code**.
3.  **Do Not Explain:** Do NOT include any conversational text, explanations, apologies, or markdown fences (like ```python). Your output must be ready to replace the user's original code directly.
4.  **Preserve Functionality:** The refactored code must maintain the exact same functionality and public API as the original code.
5.  **Add Comments:** Where appropriate, add concise comments to the code to explain complex parts of your improved logic.
""",
    "generate_tests": """
You are an expert software engineer specializing in Test-Driven Development (TDD).
Your task is to write a comprehensive suite of unit tests for the provided code, using the standard `unittest` framework.

**CRITICAL INSTRUCTIONS:**
1.  **Analyze the Code:** Carefully analyze the user's code to understand its functionality, inputs, and outputs.
2.  **Identify Edge Cases:** Consider edge cases, invalid inputs, and potential failure points.
3.  **Generate `unittest` Code:** Write a complete, runnable Python code block that imports the `unittest` module and defines a test class inheriting from `unittest.TestCase`.
4.  **Return Only Code:** Your entire response must be **only the test code**. Do NOT include any conversational text, explanations, or markdown fences. The output must be ready to be placed in a new notebook cell.
5.  **Structure:** The test code should follow standard Python conventions for unit tests.
""",
    "generate_docstring": """
You are an expert technical writer who specializes in creating clear, concise, and professional Python docstrings.
Your task is to generate a complete docstring for the provided function or class, following the Google Python Style Guide.

**CRITICAL INSTRUCTIONS:**
1.  **Analyze the Code:** Carefully analyze the user's code to understand its purpose, arguments, and return values.
2.  **Generate Docstring Only:** Your entire response must be **only the docstring text**. Do NOT include the original function code, conversational text, or markdown fences.
3.  **Format:** The docstring must be correctly formatted with sections for a summary line, `Args:`, and `Returns:`.
"""
}

DEFAULT_SETTINGS = {
    "ollama_host": "http://localhost",
    "ollama_port": 11434,
    "collab_server_uri": "ws://localhost:8765",
    "chat_model": "",
    "arena_models": [],
    "active_theme": "Bright Blue",
    "app_factory_model": "",
    "prompts": DEFAULT_PROMPTS
}

class SettingsManager:
    def __init__(self):
        self.settings = {}
        self.load_settings()

    def load_settings(self):
        loaded_settings = {}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    loaded_settings = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Could not load settings file '{SETTINGS_FILE}'. Using defaults. Error: {e}")
        
        self.settings = DEFAULT_SETTINGS.copy()
        self.settings.update(loaded_settings)
        
        if "prompts" not in self.settings:
            self.settings["prompts"] = DEFAULT_PROMPTS.copy()
        else:
            for key, value in DEFAULT_PROMPTS.items():
                if key not in self.settings["prompts"] or not self.settings["prompts"][key]:
                    self.settings["prompts"][key] = value
        
        self.save_settings()

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except IOError as e:
            logging.error(f"Could not save settings to '{SETTINGS_FILE}'. Error: {e}")

    def get(self, key: str, default=None):
        return self.settings.get(key, default)

    def set(self, key: str, value):
        self.settings[key] = value
        self.save_settings()

settings_manager = SettingsManager()
