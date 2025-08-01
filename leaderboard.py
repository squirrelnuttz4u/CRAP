# leaderboard.py
# © 2025 Colt McVey
# A widget to display the model Elo rating leaderboard.

import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QHBoxLayout, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette

# Import the global Elo system instance
from elo import elo_system

class LeaderboardWidget(QWidget):
    """
    A widget to display a leaderboard of model Elo ratings.
    """
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.refresh_leaderboard()

    def setup_ui(self):
        """Initializes the UI components and layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # --- Toolbar ---
        toolbar_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh Leaderboard")
        self.refresh_button.clicked.connect(self.refresh_leaderboard)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.refresh_button)
        
        # --- Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Rank", "Model ID", "Elo Rating"])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)

        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(self.table)

    def refresh_leaderboard(self):
        """Fetches the latest ratings and populates the table."""
        self.table.setRowCount(0) # Clear the table
        
        # The elo_system now handles loading the latest ratings automatically
        sorted_ratings = elo_system.get_all_ratings_sorted()
        
        self.table.setRowCount(len(sorted_ratings))
        
        for rank, (model_id, rating) in enumerate(sorted_ratings, 1):
            rank_item = QTableWidgetItem(str(rank))
            model_item = QTableWidgetItem(model_id)
            rating_item = QTableWidgetItem(str(rating))
            
            # Center align rank and rating
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            rating_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self.table.setItem(rank - 1, 0, rank_item)
            self.table.setItem(rank - 1, 1, model_item)
            self.table.setItem(rank - 1, 2, rating_item)

    def showEvent(self, event):
        """Override showEvent to refresh the leaderboard whenever the tab becomes visible."""
        self.refresh_leaderboard()
        super().showEvent(event)
