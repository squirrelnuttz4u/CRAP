# settings_manager.py
# © 2025 Colt McVey
# A centralized manager for application settings.

import json
import os
import logging
from data_manager import get_app_data_dir

SETTINGS_FILE = get_app_data_dir() / "app_settings.json"

# Default prompts are now part of the settings file.
DEFAULT_PROMPTS = {
    "app_factory_plan": """
You are a world-class principal software architect and DevOps engineer at a leading tech company, known for designing scalable, maintainable, and production-ready applications.

Your task is to generate a JSON object representing the complete and optimal file and directory structure for a new project based on the user's description.

**Guiding Principles:**
1.  **Modularity:** Ensure a clear separation of concerns (e.g., frontend, backend, database, configuration).
2.  **Scalability:** The structure must be logical and scalable for a growing application.
3.  **Best Practices:** Adhere to industry best practices and idiomatic conventions for the specified technology stack.
4.  **Testability:** Always include directories and placeholder files for unit and integration tests (e.g., `tests/`, `__tests__/`).
5.  **DevOps Ready:** The CI/CD pipeline in `.github/workflows/main.yml` must be practical, including steps for installing dependencies, running linters, and executing tests.

**Output Format:**
The output must be a single, clean JSON object. Do NOT include any conversational text, explanations, or markdown formatting outside of the JSON.
The JSON object must have a key "structure" which is a list of file/directory objects.
Each object in the list must have:
1. "name": The file or directory name (string).
2. "type": Either "dir" or "file" (string).
3. "children": A list of nested objects if type is "dir".
4. "purpose": A brief, clear, and actionable description of the file's specific role. This is critical, as it will be used as an instruction to generate the code for that file.
""",
    "app_factory_code": """
You are a world-class principal software engineer, renowned for writing exceptionally clean, efficient, and maintainable code. You are a master of the SOLID principles and always produce production-quality software.

The overall goal of the project you are working on is: "{user_prompt}"

Your current, specific task is to generate the **complete and fully functional source code** for the file described below.

**File Name:** `{file_name}`
**Purpose within the project:** `{purpose}`

**CRITICAL INSTRUCTIONS:**
1.  **Completeness is Mandatory:** Your output must be the entire, runnable source code for this file. Do NOT use placeholders, stubs, or comments like `// ... implementation ...`. The code must be complete and ready to be saved directly to the file.
2.  **Raw Code Only:** Your entire response must be only the raw source code. Do NOT include any conversational text, explanations, apologies, or markdown fences (like ```python).
3.  **Context is Key:** The code you write must perfectly fulfill its stated `Purpose` within the context of the `overall project goal`.
4.  **Code Quality:** The code must be idiomatic for its language, well-structured, and include comments where necessary for clarity.
""",
    "ai_chat_system": """
You are an expert AI programming assistant integrated into the CRAP IDE. Your name is CRAP.
Your primary function is to provide accurate, complete, and runnable code.

**Instructions:**
1.  When the user asks for code, provide the complete code block **first**.
2.  Do not include any conversational preamble or apologies in your response. Be direct.
3.  After the code block, you may provide a brief, concise explanation of how the code works.
4.  You will be given context from the user's attached files and their currently selected code. Use this context to inform your answer.
5.  Always use markdown code fences with the correct language identifier (e.g., ```python).
""",
    "ai_chat_project_aware": """
You are an expert AI programming assistant integrated into the CRAP IDE. Your name is CRAP.
You have been provided with the user's original high-level goal for the project and the complete architectural plan that you previously generated.
Your primary function is to help the user build, modify, or debug this specific application.

**Instructions:**
1.  Strictly adhere to the provided architectural plan.
2.  When the user asks for code, provide the complete, runnable code block **first**.
3.  After the code block, you may provide a brief, concise explanation.
4.  Always use markdown code fences with the correct language identifier (e.g., ```python).
"""
}

DEFAULT_SETTINGS = {
    "ollama_host": "[http://192.168.203.100](http://192.168.203.100)",
    "ollama_port": 11434,
    "collab_server_uri": "ws://localhost:8765",
    "chat_model": "",
    "arena_models": [],
    "active_theme": "Bright Blue",
    "app_factory_model": "",
    "prompts": DEFAULT_PROMPTS
}

class SettingsManager:
    """
    A singleton class to manage loading, accessing, and saving settings.
    """
    def __init__(self):
        self.settings = {}
        self.load_settings()

    def load_settings(self):
        """Loads settings from the JSON file, ensuring all default keys are present."""
        loaded_settings = {}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    loaded_settings = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Could not load settings file '{SETTINGS_FILE}'. Using defaults. Error: {e}")
        
        # Start with the defaults, then update with loaded settings. This is a safer merge.
        self.settings = DEFAULT_SETTINGS.copy()
        self.settings.update(loaded_settings)
        
        # Specifically handle the nested prompts dictionary to ensure all default prompts are present.
        if "prompts" not in self.settings:
            self.settings["prompts"] = DEFAULT_PROMPTS.copy()
        else:
            for key, value in DEFAULT_PROMPTS.items():
                if key not in self.settings["prompts"] or not self.settings["prompts"][key]:
                    self.settings["prompts"][key] = value
        
        # Save back to ensure the file is always complete for the next run.
        self.save_settings()

    def save_settings(self):
        """Saves the current settings to the JSON file."""
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except IOError as e:
            logging.error(f"Could not save settings to '{SETTINGS_FILE}'. Error: {e}")

    def get(self, key: str, default=None):
        """Gets a setting value by key."""
        return self.settings.get(key, default)

    def set(self, key: str, value):
        """Sets a setting value and saves it to the file."""
        self.settings[key] = value
        self.save_settings()

# Global instance
settings_manager = SettingsManager()
