# scaffolder.py
# © 2025 Colt McVey
# The user interface and backend logic for the Application Factory component.

import sys
import os
import json
import asyncio
import re
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QGroupBox, QLabel, QLineEdit, QComboBox, QTextEdit,
    QFileDialog, QTreeWidget, QTreeWidgetItem, QProgressBar, QMessageBox,
    QTextBrowser
)
from PySide6.QtCore import Qt, QObject, Signal, QThread
from PySide6.QtGui import QFont

from llm_interface import InferenceEngine
from settings_manager import settings_manager

# --- AI Planner & Scaffolding Worker ---

class ScaffoldingWorker(QObject):
    """
    Runs the AI planning and file generation in a background thread.
    """
    progress = Signal(int, str)
    finished = Signal(str)
    error = Signal(str)
    tree_item_generated = Signal(str)

    def __init__(self, engine: InferenceEngine, user_prompt: str, project_dir: str, project_name: str):
        super().__init__()
        self.engine = engine
        self.user_prompt = user_prompt
        self.project_dir = project_dir
        self.project_name = project_name
        self.is_running = True
        self.model_id = None

    def stop(self):
        self.is_running = False

    async def _select_model(self):
        """Selects the best available model for scaffolding based on settings."""
        factory_model = settings_manager.get("app_factory_model")
        if factory_model:
            self.model_id = factory_model
            return True
            
        if 'openai' in self.engine.providers:
            self.model_id = "openai/gpt-4o"
            return True
        elif 'ollama' in self.engine.providers:
            models = await self.engine.providers['ollama'].list_models()
            if models:
                preferred_models = ['llama3', 'codellama', 'mistral']
                for pm in preferred_models:
                    for m in models:
                        if pm in m:
                            self.model_id = f"ollama/{m}"
                            return True
                self.model_id = f"ollama/{models[0]}"
                return True
        
        self.error.emit("No suitable AI provider found. Please configure a model in Settings -> App Factory.")
        return False

    async def run(self):
        """The main async method to be run."""
        try:
            if not await self._select_model():
                return

            if not self.is_running: return
            self.progress.emit(10, f"Asking AI ({self.model_id}) to plan project structure...")
            
            plan = await self._get_project_plan()
            if not plan or not self.is_running:
                return

            self.progress.emit(30, "AI plan received. Generating project files...")
            
            root_path = os.path.join(self.project_dir, self.project_name)
            os.makedirs(root_path, exist_ok=True)

            crap_dir = os.path.join(root_path, ".crap")
            os.makedirs(crap_dir, exist_ok=True)
            with open(os.path.join(crap_dir, "project_plan.json"), 'w') as f:
                json.dump(plan, f, indent=2)
            with open(os.path.join(crap_dir, "user_prompt.txt"), 'w') as f:
                f.write(self.user_prompt)

            await self._generate_structure_and_content(plan.get('structure', []), root_path)
            
            if self.is_running:
                self.progress.emit(100, "Project generation complete!")
                self.finished.emit(f"Project '{self.project_name}' created successfully!")

        except Exception as e:
            self.error.emit(f"An unexpected error occurred: {e}")

    def _repair_json(self, json_string: str) -> str:
        """Attempts to fix common JSON errors from LLMs, like trailing commas."""
        json_string = re.sub(r",\s*([\}\]])", r"\1", json_string)
        return json_string

    async def _get_project_plan(self) -> dict | None:
        """Uses the LLM to generate a JSON structure for the project."""
        system_prompt = settings_manager.get("prompts").get("app_factory_plan")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self.user_prompt}
        ]
        
        streams = await self.engine.battle([self.model_id], messages)
        full_response = "".join([token async for token in streams[0]])
        
        if full_response.strip().startswith("[Error:"):
            self.error.emit(f"AI provider error: {full_response}")
            return None
        
        try:
            json_str = None
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', full_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                brace_match = re.search(r'(\{.*?\})', full_response, re.DOTALL)
                if brace_match:
                    json_str = brace_match.group(1)

            if json_str:
                repaired_json_str = self._repair_json(json_str)
                return json.loads(repaired_json_str)
            else:
                raise ValueError("No valid JSON object found in the AI's response.")

        except (json.JSONDecodeError, ValueError) as e:
            self.error.emit(f"AI returned invalid JSON for the project plan. Error: {e}")
            print("---INVALID AI RESPONSE---")
            print(full_response)
            print("-------------------------")
            return None

    async def _generate_structure_and_content(self, structure: list, current_path: str):
        """Recursively creates the structure and generates content for each file."""
        for item in structure:
            if not self.is_running: return
            item_path = os.path.join(current_path, item['name'])
            if item['type'] == 'dir':
                os.makedirs(item_path, exist_ok=True)
                self.tree_item_generated.emit(item_path)
                if 'children' in item:
                    await self._generate_structure_and_content(item['children'], item_path)
            elif item['type'] == 'file':
                self.progress.emit(50, f"Generating content for: {item['name']}...")
                file_content = await self._generate_file_content(item['name'], item['purpose'])
                if not file_content.strip().startswith("[Error:"):
                    with open(item_path, 'w', encoding='utf-8') as f:
                        f.write(file_content)
                    self.tree_item_generated.emit(item_path)
            await asyncio.sleep(0.01)

    async def _generate_file_content(self, file_name: str, purpose: str) -> str:
        """Asks the AI to generate the code for a single file."""
        system_prompt = settings_manager.get("prompts").get("app_factory_code")
        formatted_prompt = system_prompt.format(user_prompt=self.user_prompt, file_name=file_name, purpose=purpose)
        messages = [{"role": "user", "content": formatted_prompt}]
        streams = await self.engine.battle([self.model_id], messages)
        raw_content = "".join([token async for token in streams[0]])
        
        # --- Cleanup Logic ---
        cleaned_content = raw_content.strip()
        
        if cleaned_content.startswith("```") and cleaned_content.endswith("```"):
            lines = cleaned_content.splitlines()
            cleaned_content = "\n".join(lines[1:-1])
            
        if cleaned_content.startswith("'''") and cleaned_content.endswith("'''"):
            cleaned_content = cleaned_content[3:-3].strip()

        return cleaned_content


class ScaffolderWidget(QWidget):
    """
    A widget for the App Factory, used to scaffold new application projects.
    """
    def __init__(self):
        super().__init__()
        self.engine = InferenceEngine()
        self.worker_thread = None
        self.async_worker = None
        self.setup_ui()

    def setup_ui(self):
        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # --- Column 1: Configuration ---
        config_column = QVBoxLayout()
        prompt_group = QGroupBox("1. Describe Your Application")
        prompt_layout = QVBoxLayout(prompt_group)
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("e.g., 'A full-stack web app for a book review blog...'")
        self.prompt_edit.setMinimumHeight(120)
        prompt_layout.addWidget(self.prompt_edit)
        
        details_group = QGroupBox("2. Configure Project Details")
        details_layout = QGridLayout(details_group)
        self.project_name_edit = QLineEdit()
        self.project_dir_edit = QLineEdit()
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._browse_directory)
        details_layout.addWidget(QLabel("Project Name:"), 0, 0); details_layout.addWidget(self.project_name_edit, 0, 1)
        details_layout.addWidget(QLabel("Project Directory:"), 1, 0); details_layout.addWidget(self.project_dir_edit, 1, 1); details_layout.addWidget(self.browse_button, 1, 2)
        
        config_column.addWidget(prompt_group); config_column.addWidget(details_group); config_column.addStretch()

        # --- Column 2: Output and Generation ---
        output_column = QVBoxLayout()
        
        preview_group = QGroupBox("Generated Project Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["Project Structure"])
        preview_layout.addWidget(self.file_tree)

        log_group = QGroupBox("Generation Log")
        log_layout = QVBoxLayout(log_group)
        self.log_browser = QTextBrowser()
        self.log_browser.setReadOnly(True)
        log_layout.addWidget(self.log_browser)

        self.generate_button = QPushButton("Generate Application")
        self.generate_button.setMinimumHeight(45)
        self.generate_button.clicked.connect(self._toggle_generation)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        output_column.addWidget(preview_group, 1)
        output_column.addWidget(log_group, 1)
        output_column.addWidget(self.progress_bar)
        output_column.addWidget(self.generate_button)

        main_layout.addLayout(config_column, 0, 0); main_layout.addLayout(output_column, 0, 1)
        main_layout.setColumnStretch(0, 1); main_layout.setColumnStretch(1, 1)

    def _toggle_generation(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.log_browser.append("Stopping generation...")
            if self.async_worker:
                self.async_worker.stop()
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.generate_button.setText("Generate Application")
            self.progress_bar.setVisible(False)
        else:
            self._start_generation()

    def _start_generation(self):
        user_prompt = self.prompt_edit.toPlainText().strip()
        project_dir = self.project_dir_edit.text().strip()
        project_name = self.project_name_edit.text().strip()

        if not all([user_prompt, project_dir, project_name]):
            self.log_browser.setText("<font color='red'>Error: Please fill in all fields.</font>")
            return

        self.log_browser.clear()
        self.file_tree.clear()
        self.tree_items = {}
        
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.generate_button.setText("Stop Generation")

        self.worker_thread = QThread()
        self.async_worker = ScaffoldingWorker(self.engine, user_prompt, project_dir, project_name)
        self.async_worker.moveToThread(self.worker_thread)

        self.async_worker.progress.connect(lambda p, m: (self.progress_bar.setValue(p), self.log_browser.append(m)))
        self.async_worker.tree_item_generated.connect(self._add_tree_item)
        self.async_worker.finished.connect(self._on_generation_finished)
        self.async_worker.error.connect(self._on_generation_error)
        
        self.worker_thread.started.connect(lambda: asyncio.create_task(self.async_worker.run()))
        self.worker_thread.start()

    def _add_tree_item(self, item_path: str):
        """Adds a new file or directory to the preview tree."""
        parent_path, item_name = os.path.split(item_path)
        
        if parent_path in self.tree_items:
            parent_item = self.tree_items[parent_path]
        else:
            # Should be the root
            parent_item = self.file_tree.invisibleRootItem()

        new_item = QTreeWidgetItem(parent_item, [item_name])
        self.tree_items[item_path] = new_item


    def _on_generation_finished(self, message):
        self.log_browser.append(f"<font color='green'>{message}</font>")
        self.progress_bar.setValue(100)
        self.generate_button.setText("Generate Application")
        self.worker_thread.quit()

    def _on_generation_error(self, message):
        self.log_browser.append(f"<font color='red'>Error: {message}</font>")
        self.progress_bar.setVisible(False)
        self.generate_button.setText("Generate Application")
        self.worker_thread.quit()

    def _browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if directory:
            self.project_dir_edit.setText(directory)
