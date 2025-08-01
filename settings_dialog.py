# settings_dialog.py
# © 2025 Colt McVey
# A dialog for editing application settings.

import asyncio
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QDialogButtonBox, QSpinBox, QGroupBox, QLabel,
    QListWidget, QListWidgetItem, QComboBox, QTabWidget, QWidget, QTextEdit
)
from PySide6.QtCore import Qt
from typing import List

from settings_manager import settings_manager
from theme_manager import theme_manager
from llm_interface import InferenceEngine

class SettingsDialog(QDialog):
    """
    A dialog window for viewing and editing application settings.
    """
    def __init__(self, available_models: List[str], parent=None):
        super().__init__(parent)
        self.engine = InferenceEngine()
        self.available_models = available_models
        self.setWindowTitle("Application Settings")
        self.setMinimumSize(600, 700)
        self.setup_ui()
        self.load_settings()
        # If the initial model list is empty, try to populate it again.
        if not self.available_models:
            asyncio.create_task(self.populate_model_lists())

    def setup_ui(self):
        """Initializes the UI components and layout."""
        main_layout = QVBoxLayout(self)
        tabs = QTabWidget()
        
        # --- General Tab ---
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        
        theme_group = QGroupBox("Theme & Appearance")
        theme_layout = QFormLayout(theme_group)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(theme_manager.get_theme_names())
        theme_layout.addRow("Active Theme:", self.theme_combo)
        
        model_group = QGroupBox("Model Defaults")
        model_layout = QFormLayout(model_group)
        self.chat_model_combo = QComboBox()
        model_layout.addRow("Default Chat Model:", self.chat_model_combo)

        factory_group = QGroupBox("App Factory Settings")
        factory_layout = QFormLayout(factory_group)
        self.factory_model_combo = QComboBox()
        factory_layout.addRow("Scaffolding Model:", self.factory_model_combo)

        arena_group = QGroupBox("Model Arena Settings")
        arena_layout = QVBoxLayout(arena_group)
        arena_layout.addWidget(QLabel("Models for Random Arena Battle:"))
        self.arena_models_list = QListWidget()
        self.arena_models_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        arena_layout.addWidget(self.arena_models_list)

        ollama_group = QGroupBox("Ollama Server Configuration")
        ollama_layout = QFormLayout(ollama_group)
        self.ollama_host_edit = QLineEdit()
        self.ollama_port_edit = QSpinBox()
        self.ollama_port_edit.setRange(1, 65535)
        ollama_layout.addRow("Host URL:", self.ollama_host_edit)
        ollama_layout.addRow("Port:", self.ollama_port_edit)
        
        general_layout.addWidget(theme_group)
        general_layout.addWidget(model_group)
        general_layout.addWidget(factory_group)
        general_layout.addWidget(arena_group)
        general_layout.addWidget(ollama_group)
        general_layout.addStretch()

        # --- Prompts Tab ---
        prompts_tab = QWidget()
        prompts_layout = QVBoxLayout(prompts_tab)
        
        plan_group = QGroupBox("App Factory: Planning Prompt")
        plan_layout = QVBoxLayout(plan_group)
        self.plan_prompt_edit = QTextEdit()
        plan_layout.addWidget(self.plan_prompt_edit)
        
        code_group = QGroupBox("App Factory: Code Generation Prompt")
        code_layout = QVBoxLayout(code_group)
        self.code_prompt_edit = QTextEdit()
        code_layout.addWidget(self.code_prompt_edit)
        
        chat_group = QGroupBox("AI Chat: System Prompt")
        chat_layout = QVBoxLayout(chat_group)
        self.chat_prompt_edit = QTextEdit()
        chat_layout.addWidget(self.chat_prompt_edit)

        project_chat_group = QGroupBox("AI Chat: Project-Aware System Prompt")
        project_chat_layout = QVBoxLayout(project_chat_group)
        self.project_chat_prompt_edit = QTextEdit()
        project_chat_layout.addWidget(self.project_chat_prompt_edit)
        
        prompts_layout.addWidget(plan_group)
        prompts_layout.addWidget(code_group)
        prompts_layout.addWidget(chat_group)
        prompts_layout.addWidget(project_chat_group)

        tabs.addTab(general_tab, "General")
        tabs.addTab(prompts_tab, "System Prompts")

        main_layout.addWidget(tabs)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    async def populate_model_lists(self):
        """Asynchronously fetches all models and populates the UI."""
        all_models_dict = await self.engine.get_all_models()
        self.available_models = [f"{p}/{m}" for p, models in all_models_dict.items() for m in models]
        
        self.populate_model_lists_from_cache()
        self.load_model_settings()

    def load_settings(self):
        """Loads all non-model settings into the UI fields."""
        self.theme_combo.setCurrentText(settings_manager.get("active_theme"))
        self.ollama_host_edit.setText(settings_manager.get("ollama_host"))
        self.ollama_port_edit.setValue(settings_manager.get("ollama_port"))
        
        prompts = settings_manager.get("prompts")
        self.plan_prompt_edit.setPlainText(prompts.get("app_factory_plan", ""))
        self.code_prompt_edit.setPlainText(prompts.get("app_factory_code", ""))
        self.chat_prompt_edit.setPlainText(prompts.get("ai_chat_system", ""))
        self.project_chat_prompt_edit.setPlainText(prompts.get("ai_chat_project_aware", ""))
        
        # Populate initial lists from the passed-in models
        self.populate_model_lists_from_cache()
        self.load_model_settings()

    def populate_model_lists_from_cache(self):
        """Populates UI elements with the already-fetched model list."""
        model_list_with_blank = [""] + self.available_models
        self.chat_model_combo.clear()
        self.factory_model_combo.clear()
        self.chat_model_combo.addItems(model_list_with_blank)
        self.factory_model_combo.addItems(model_list_with_blank)
        
        self.arena_models_list.clear()
        if not self.available_models:
            item = QListWidgetItem("No models found.")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            self.arena_models_list.addItem(item)
        else:
            for model_name in self.available_models:
                item = QListWidgetItem(model_name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.arena_models_list.addItem(item)

    def load_model_settings(self):
        """Loads only the model-related settings, to be called after models are populated."""
        self.chat_model_combo.setCurrentText(settings_manager.get("chat_model"))
        self.factory_model_combo.setCurrentText(settings_manager.get("app_factory_model"))
        
        selected_arena_models = settings_manager.get("arena_models", [])
        for i in range(self.arena_models_list.count()):
            item = self.arena_models_list.item(i)
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                if item.text() in selected_arena_models:
                    item.setCheckState(Qt.CheckState.Checked)

    def accept(self):
        """Saves the settings when OK is clicked."""
        settings_manager.set("active_theme", self.theme_combo.currentText())
        settings_manager.set("chat_model", self.chat_model_combo.currentText())
        settings_manager.set("app_factory_model", self.factory_model_combo.currentText())
        settings_manager.set("ollama_host", self.ollama_host_edit.text().strip())
        settings_manager.set("ollama_port", self.ollama_port_edit.value())
        
        selected_arena_models = []
        for i in range(self.arena_models_list.count()):
            item = self.arena_models_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_arena_models.append(item.text())
        settings_manager.set("arena_models", selected_arena_models)

        prompts = {
            "app_factory_plan": self.plan_prompt_edit.toPlainText(),
            "app_factory_code": self.code_prompt_edit.toPlainText(),
            "ai_chat_system": self.chat_prompt_edit.toPlainText(),
            "ai_chat_project_aware": self.project_chat_prompt_edit.toPlainText()
        }
        settings_manager.set("prompts", prompts)
        
        super().accept()
