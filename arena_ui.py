# arena_ui.py
# © 2025 Colt McVey
# The user interface for the Model Arena component.

import sys
import json
import asyncio
import random
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTextEdit, QTextBrowser, QPushButton, QGroupBox, QLabel, QFrame, QDialog,
    QComboBox, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer
from PySide6.QtGui import QFont, QPalette, QColor

from prompt_editor import PromptEditorDialog
from llm_interface import InferenceEngine
from elo import elo_system
from settings_manager import settings_manager

class AsyncWorker(QObject):
    """Runs async tasks in a way that can communicate with the Qt UI."""
    finished = Signal()
    new_token = Signal(int, str)
    error = Signal(str)

    def __init__(self, engine, models, messages):
        super().__init__()
        self.engine = engine; self.models = models; self.messages = messages
        self.is_running = True

    async def run(self):
        try:
            streams = await self.engine.battle(self.models, self.messages)
            tasks = [self._consume_stream(i, stream) for i, stream in enumerate(streams)]
            await asyncio.gather(*tasks)
        except Exception as e:
            self.error.emit(f"Failed to start battle: {e}")
        finally:
            if self.is_running: self.finished.emit()

    async def _consume_stream(self, panel_index, stream):
        try:
            async for token in stream:
                if not self.is_running: break
                self.new_token.emit(panel_index, token)
        except Exception as e:
            self.error.emit(f"Error in stream {panel_index}: {e}")

    def stop(self):
        self.is_running = False

class ArenaWidget(QWidget):
    """
    A widget for the Model Arena, allowing side-by-side comparison of LLM outputs.
    """
    def __init__(self):
        super().__init__()
        self.engine = InferenceEngine()
        self.async_worker = None
        self.all_models = []
        self.current_battle_models = {}
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        prompt_group = QGroupBox("Your Prompt")
        prompt_layout = QVBoxLayout(prompt_group)
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Enter a simple prompt here, or use the Advanced Editor...")
        
        controls_layout = QHBoxLayout()
        self.anonymous_mode_checkbox = QCheckBox("Anonymous Battle Mode")
        self.anonymous_mode_checkbox.setChecked(True)
        self.anonymous_mode_checkbox.toggled.connect(self._on_mode_toggled)
        
        self.advanced_prompt_button = QPushButton("Advanced Editor...")
        self.advanced_prompt_button.clicked.connect(self._open_advanced_editor)
        
        self.generate_button = QPushButton("Random Battle!")
        self.generate_button.clicked.connect(self._on_generate_clicked)
        
        controls_layout.addWidget(self.anonymous_mode_checkbox)
        controls_layout.addWidget(self.advanced_prompt_button)
        controls_layout.addStretch()
        controls_layout.addWidget(self.generate_button)
        
        prompt_layout.addWidget(self.prompt_input)
        prompt_layout.addLayout(controls_layout)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.model_a_widget = self._create_model_panel("Model A")
        self.model_b_widget = self._create_model_panel("Model B")
        self.splitter.addWidget(self.model_a_widget)
        self.splitter.addWidget(self.model_b_widget)

        vote_group = QGroupBox("Cast Your Vote")
        vote_layout = QHBoxLayout(vote_group)
        self.vote_a_button = QPushButton("⬅️ Model A is Better")
        self.vote_b_button = QPushButton("Model B is Better ➡️")
        self.vote_tie_button = QPushButton("🤝 It's a Tie")
        self.vote_bad_button = QPushButton("👎 Both are Bad")
        self.vote_buttons = [self.vote_a_button, self.vote_b_button, self.vote_tie_button, self.vote_bad_button]
        for button in self.vote_buttons:
            vote_layout.addWidget(button)
            button.setEnabled(False)
            
        self.vote_a_button.clicked.connect(lambda: self._cast_vote("win_a"))
        self.vote_b_button.clicked.connect(lambda: self._cast_vote("win_b"))
        self.vote_tie_button.clicked.connect(lambda: self._cast_vote("draw"))
        self.vote_bad_button.clicked.connect(lambda: self._cast_vote("bad"))

        main_layout.addWidget(prompt_group)
        main_layout.addWidget(self.splitter, 1)
        main_layout.addWidget(vote_group)

        self._on_mode_toggled(True)

    def populate_models(self, all_models: list):
        """Populates the dropdowns with a pre-fetched list of models."""
        self.all_models = all_models
        self.model_a_widget.findChild(QComboBox).addItems(self.all_models)
        self.model_b_widget.findChild(QComboBox).addItems(self.all_models)
        if len(self.all_models) > 1:
             self.model_b_widget.findChild(QComboBox).setCurrentIndex(1)

    def _on_generate_clicked(self):
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt: return

        model_a_id, model_b_id = None, None
        if self.anonymous_mode_checkbox.isChecked():
            arena_models = settings_manager.get("arena_models", [])
            model_pool = arena_models if arena_models and len(arena_models) >= 2 else self.all_models
            if len(model_pool) < 2:
                QMessageBox.warning(self, "Not Enough Models", 
                                    "Anonymous battle requires at least two available models.\n"
                                    "Please select more models in Settings -> Model Defaults.")
                return
            model_a_id, model_b_id = random.sample(model_pool, 2)
        else:
            model_a_id = self.model_a_widget.findChild(QComboBox).currentText()
            model_b_id = self.model_b_widget.findChild(QComboBox).currentText()
        
        if not model_a_id or not model_b_id or model_a_id == model_b_id:
            QMessageBox.warning(self, "Invalid Selection", "Please select two different models to compare.")
            return

        self.current_battle_models = {"a": model_a_id, "b": model_b_id}
        self.set_ui_for_battle(True)
        self.model_a_widget.findChild(QTextBrowser).clear()
        self.model_b_widget.findChild(QTextBrowser).clear()
        
        messages = [{"role": "user", "content": prompt}]
        self.async_worker = AsyncWorker(self.engine, [model_a_id, model_b_id], messages)
        self.async_worker.new_token.connect(self._on_new_token)
        self.async_worker.finished.connect(self._on_battle_finished)
        self.async_worker.error.connect(self._on_battle_error)
        asyncio.create_task(self.async_worker.run())

    def _cast_vote(self, outcome: str):
        if not self.current_battle_models: return
        model_a_id = self.current_battle_models["a"]
        model_b_id = self.current_battle_models["b"]
        if outcome != "bad":
            elo_system.update_ratings(model_a_id, model_b_id, outcome)
        self._update_panel_after_vote(self.model_a_widget, model_a_id)
        self._update_panel_after_vote(self.model_b_widget, model_b_id)
        for button in self.vote_buttons:
            button.setEnabled(False)

    def _update_panel_after_vote(self, panel_widget: QWidget, model_id: str):
        name_label = panel_widget.findChild(QLabel, "nameLabel")
        score_label = panel_widget.findChild(QLabel, "scoreLabel")
        name_label.setText(f"<strong>{model_id}</strong>")
        score_label.setText(f"Elo: {elo_system.get_rating(model_id)}")

    def _on_new_token(self, panel_index, token):
        panel = self.model_a_widget if panel_index == 0 else self.model_b_widget
        panel.findChild(QTextBrowser).insertPlainText(token)

    def _on_battle_finished(self):
        self.set_ui_for_battle(False); self.async_worker = None

    def _on_battle_error(self, error_message):
        print(f"BATTLE ERROR: {error_message}"); self._on_battle_finished()

    def set_ui_for_battle(self, is_battling):
        self.generate_button.setEnabled(not is_battling)
        self.prompt_input.setReadOnly(is_battling)
        for button in self.vote_buttons: button.setEnabled(not is_battling)
        if is_battling:
            self._reset_panel_for_battle(self.model_a_widget, "Model A")
            self._reset_panel_for_battle(self.model_b_widget, "Model B")
            
    def _on_mode_toggled(self, checked):
        self.model_a_widget.findChild(QComboBox).setVisible(not checked)
        self.model_b_widget.findChild(QComboBox).setVisible(not checked)
        self.model_a_widget.findChild(QLabel, "nameLabel").setVisible(checked)
        self.model_b_widget.findChild(QLabel, "nameLabel").setVisible(checked)
        self.generate_button.setText("Random Battle!" if checked else "Compare Models")

    def _reset_panel_for_battle(self, panel_widget: QWidget, placeholder_name: str):
        panel_widget.findChild(QLabel, "nameLabel").setText(f"<strong>{placeholder_name}</strong>")
        panel_widget.findChild(QLabel, "scoreLabel").setText("Elo: ?")

    def _create_model_panel(self, placeholder: str) -> QWidget:
        panel = QWidget(); layout = QVBoxLayout(panel); header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame); name_label = QLabel(f"<strong>{placeholder}</strong>")
        name_label.setObjectName("nameLabel"); model_combo = QComboBox()
        score_label = QLabel("Elo: ?"); score_label.setObjectName("scoreLabel")
        header_layout.addWidget(name_label); header_layout.addWidget(model_combo)
        header_layout.addStretch(); header_layout.addWidget(score_label)
        output_browser = QTextBrowser(); output_browser.setReadOnly(True)
        layout.addWidget(header_frame); layout.addWidget(output_browser)
        return panel

    def _open_advanced_editor(self):
        dialog = PromptEditorDialog("ArenaPrompt", self)
        if dialog.exec():
            prompt_data = dialog.get_prompt_data_from_ui()
            display_text = f"Instruction: {prompt_data['instruction']}\n\nContext: {prompt_data['context']}"
            self.prompt_input.setPlainText(display_text)
