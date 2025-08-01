# prompt_manager.py
# © 2025 Colt McVey
# A version control system for managing prompts.

import os
import json
import hashlib
import datetime
from typing import Dict, List, Optional
from data_manager import get_app_data_dir

# The prompts directory is now located in the user's app data directory.
PROMPTS_DIR = get_app_data_dir() / "prompts"

class PromptVersion:
    """Represents a single, immutable version of a prompt."""
    def __init__(self, prompt_data: Dict, version_id: str, message: str):
        self.data = prompt_data
        self.version_id = version_id
        self.message = message
        self.timestamp = datetime.datetime.now().isoformat()

    def to_dict(self):
        return {
            "version_id": self.version_id,
            "timestamp": self.timestamp,
            "message": self.message,
            "data": self.data
        }

class Prompt:
    """Manages the history and versions of a single named prompt."""
    def __init__(self, name: str):
        self.name = name
        self.file_path = PROMPTS_DIR / f"{self.name}.json"
        self.versions: Dict[str, PromptVersion] = {}
        self.head: Optional[str] = None # Points to the version_id of the latest version
        self._load()

    def _load(self):
        """Loads the prompt's version history from its file."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    data = json.load(f)
                    self.head = data.get("head")
                    for v_data in data.get("versions", []):
                        version = PromptVersion(v_data['data'], v_data['version_id'], v_data['message'])
                        version.timestamp = v_data['timestamp']
                        self.versions[version.version_id] = version
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading prompt '{self.name}': {e}")

    def _save(self):
        """Saves the prompt's entire history to its file."""
        PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
        
        data = {
            "name": self.name,
            "head": self.head,
            "versions": [v.to_dict() for v in self.versions.values()]
        }
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=4)

    def commit(self, prompt_data: Dict, message: str) -> str:
        """Creates a new version of the prompt."""
        # Create a stable hash of the prompt data to use as an ID
        data_str = json.dumps(prompt_data, sort_keys=True).encode('utf-8')
        version_id = hashlib.sha1(data_str).hexdigest()

        if version_id in self.versions:
            # This exact version already exists, no need to commit
            return version_id

        new_version = PromptVersion(prompt_data, version_id, message)
        self.versions[version_id] = new_version
        self.head = version_id
        self._save()
        print(f"Committed new version '{version_id}' for prompt '{self.name}'")
        return version_id

    def get_latest_version(self) -> Optional[PromptVersion]:
        """Returns the latest (HEAD) version of the prompt."""
        if self.head:
            return self.versions.get(self.head)
        return None

    def get_version(self, version_id: str) -> Optional[PromptVersion]:
        """Returns a specific version of the prompt by its ID."""
        return self.versions.get(version_id)

class PromptManager:
    """A global service to discover and manage all prompts."""
    def __init__(self):
        self.prompts: Dict[str, Prompt] = {}
        self.discover_prompts()

    def discover_prompts(self):
        """Finds all prompt files in the prompts directory."""
        if not os.path.exists(PROMPTS_DIR):
            return
        for filename in os.listdir(PROMPTS_DIR):
            if filename.endswith(".json"):
                prompt_name = os.path.splitext(filename)[0]
                self.prompts[prompt_name] = Prompt(prompt_name)

    def get_prompt(self, name: str) -> Prompt:
        """Gets a prompt by name, creating it if it doesn't exist."""
        if name not in self.prompts:
            self.prompts[name] = Prompt(name)
        return self.prompts[name]

# --- Global Instance ---
prompt_manager = PromptManager()
