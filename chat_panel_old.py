# chat_panel.py
# © 2025 Colt McVey
# A dockable chat panel for conversational AI interaction with history.

import sys
import os
import asyncio
import json
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit,
    QPushButton, QHBoxLayout, QFrame, QLabel, QScrollArea,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QSize
from PySide6.QtGui import QFont, QTextCursor

from llm_interface import InferenceEngine
from settings_manager import settings_manager
from message_widgets import AIMessageBubble
from ui_utils import create_icon_from_svg, SVG_ICONS

PROMPT_SIZE_WARNING_THRESHOLD = 512 * 1024

class ChatWorker(QObject):
    """
    Runs a chat completion and emits the full response when finished.
    """
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, engine: InferenceEngine, model_id: str, messages: list):
        super().__init__()
        self.engine = engine
        self.model_id = model_id
        self.messages = messages

    async def run(self):
        """Generates the full response and emits it."""
        try:
            streams = await self.engine.battle([self.model_id], self.messages)
            full_response = "".join([token async for token in streams[0]])
            self.finished.emit(full_response)
        except Exception as e:
            self.error.emit(f"Chat Error: {e}")

class ChatPanel(QWidget):
    """
    A widget for conversational AI, using custom widgets for each message.
    """
    insert_code_in_notebook = Signal(str)
    add_to_scratchpad = Signal(str)

    def __init__(self):
        super().__init__()
        self.engine = InferenceEngine()
        self.chat_worker = None
        self.editor_context = ""
        self.file_context = []
        self.project_context = {}
        self.chat_history = [] # Stores the conversation history
        self.setup_ui()

    def setup_ui(self):
        """Initializes the UI components and layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # --- Header with New Chat button ---
        header_layout = QHBoxLayout()
        self.new_chat_button = QPushButton("New Chat")
        self.new_chat_button.clicked.connect(self.new_chat)
        header_layout.addWidget(QLabel("<b>AI Chat</b>"))
        header_layout.addStretch()
        header_layout.addWidget(self.new_chat_button)

        # --- History Area ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.history_container = QWidget()
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.addStretch() # Pushes messages to the top
        
        self.scroll_area.setWidget(self.history_container)

        # --- Input Area ---
        input_frame = QFrame()
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(0, 5, 0, 0)
        
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("Ask the AI about your code and attached files...")
        self.input_edit.setMaximumHeight(80)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(self.send_button, alignment=Qt.AlignmentFlag.AlignRight)

        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.scroll_area, 1) 
        main_layout.addWidget(input_frame, 0)

    def new_chat(self):
        """Clears the chat history and the UI."""
        self.chat_history = []
        # Clear all widgets from the history layout
        while self.history_layout.count() > 1: # Keep the stretch
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.send_button.setEnabled(True)
        if hasattr(self, 'thinking_label') and self.thinking_label:
            self.thinking_label.deleteLater()
            self.thinking_label = None

    def add_message_widget(self, widget: QWidget):
        """Adds a new message bubble to the history."""
        self.history_layout.insertWidget(self.history_layout.count() - 1, widget)
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    def set_editor_context(self, context_text: str, file_path: str = None):
        """Receives context from the active editor and checks for a project plan."""
        self.editor_context = context_text
        self.project_context = {}
        if file_path:
            current_dir = os.path.dirname(file_path)
            while len(current_dir) > 3:
                crap_dir = os.path.join(current_dir, ".crap")
                if os.path.isdir(crap_dir):
                    try:
                        plan_path = os.path.join(crap_dir, "project_plan.json")
                        prompt_path = os.path.join(crap_dir, "user_prompt.txt")
                        if os.path.exists(plan_path) and os.path.exists(prompt_path):
                            with open(plan_path, 'r') as f: self.project_context['plan'] = f.read()
                            with open(prompt_path, 'r') as f: self.project_context['prompt'] = f.read()
                            break
                    except Exception as e:
                        print(f"Error loading project context: {e}")
                        break
                current_dir = os.path.dirname(current_dir)

    def set_file_context(self, files: list):
        """Receives the list of active context files from the file browser."""
        self.file_context = files

    def send_message(self):
        """Sends the user's message and all context to the AI."""
        user_message = self.input_edit.toPlainText().strip()
        if not user_message: return

        chat_model = settings_manager.get("chat_model")
        if not chat_model:
            self.on_error("No default chat model has been configured in Settings.")
            return

        user_bubble = QLabel(f"<b>You:</b><br>{user_message}")
        user_bubble.setWordWrap(True); user_bubble.setObjectName("userMessageBubble")
        self.add_message_widget(user_bubble)
        self.input_edit.clear()
        
        system_prompt = settings_manager.get("prompts").get("ai_chat_project_aware") if self.project_context else settings_manager.get("prompts").get("ai_chat_system")
        
        messages = [{"role": "system", "content": system_prompt}]
        
        context_prompt = "Based on the following context:\n\n"
        if self.project_context:
            context_prompt += f"--- Original User Goal ---\n{self.project_context['prompt']}\n\n"
            context_prompt += f"--- Project Architecture Plan ---\n{self.project_context['plan']}\n\n"
        if self.file_context:
            context_prompt += "--- Attached Files ---\n"
            for file_info in self.file_context:
                context_prompt += f"File: `{file_info['path']}`\n```\n{file_info['content']}\n```\n\n"
        if self.editor_context:
            context_prompt += f"--- Selected Code in Editor ---\n```\n{self.editor_context}\n```\n\n"
        
        messages[0]["content"] += "\n\n" + context_prompt
        
        messages.extend(self.chat_history)
        messages.append({"role": "user", "content": user_message})
        self.chat_history.append({"role": "user", "content": user_message})
        
        full_prompt_for_check = json.dumps(messages)
        if len(full_prompt_for_check) > PROMPT_SIZE_WARNING_THRESHOLD:
            reply = QMessageBox.warning(self, "Large Context Warning",
                f"The total context size is very large ({len(full_prompt_for_check):,} characters) and may be rejected by the AI server.\n\n"
                "Do you want to proceed anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return

        self.thinking_label = QLabel(f"<i>AI ({chat_model}) is thinking...</i>")
        self.add_message_widget(self.thinking_label)
        self.send_button.setEnabled(False)
        
        self.chat_worker = ChatWorker(self.engine, chat_model, messages)
        self.chat_worker.finished.connect(self.on_finished)
        self.chat_worker.error.connect(self.on_error)
        asyncio.create_task(self.chat_worker.run())

    def on_finished(self, full_response: str):
        """Called when the AI response is complete."""
        if hasattr(self, 'thinking_label') and self.thinking_label:
            self.thinking_label.deleteLater(); self.thinking_label = None
        
        self.chat_history.append({"role": "assistant", "content": full_response})
        
        ai_bubble = AIMessageBubble(full_response)
        ai_bubble.insert_code_requested.connect(self.insert_code_in_notebook)
        ai_bubble.add_to_scratchpad_requested.connect(self.add_to_scratchpad)
        self.add_message_widget(ai_bubble)
        
        self.send_button.setEnabled(True)

    def on_error(self, error_message: str):
        if hasattr(self, 'thinking_label') and self.thinking_label:
            self.thinking_label.deleteLater(); self.thinking_label = None
            
        error_label = QLabel(f"<font color='#e74c3c'>{error_message}</font>")
        self.add_message_widget(error_label)
        
        self.send_button.setEnabled(True)
