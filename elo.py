# elo.py
# © 2025 Colt McVey
# A simple implementation of the Elo rating system with persistence.

import math
import json
import os
import logging
from data_manager import get_app_data_dir

# The rating file is now located in the user's app data directory.
RATING_FILE = get_app_data_dir() / "elo_ratings.json"

class EloRatingSystem:
    """
    Manages Elo ratings for a collection of players (or AI models).
    Ratings are persisted to a local JSON file.
    """
    def __init__(self, k_factor=32, initial_rating=1200):
        """
        Initializes the Elo system.
        
        Args:
            k_factor: The K-factor determines how much ratings change after a match.
            initial_rating: The rating assigned to a new, unranked model.
        """
        self.ratings = {}
        self.k_factor = k_factor
        self.initial_rating = initial_rating
        self.load_ratings()

    def load_ratings(self):
        """Loads ratings from the JSON file if it exists."""
        if os.path.exists(RATING_FILE):
            try:
                with open(RATING_FILE, 'r') as f:
                    self.ratings = json.load(f)
                logging.info(f"Elo ratings loaded from {RATING_FILE}")
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Could not load ratings file. Starting fresh. Error: {e}")
                self.ratings = {}
        else:
            logging.info("No ratings file found. Starting with fresh ratings.")

    def save_ratings(self):
        """Saves the current ratings to the JSON file."""
        try:
            with open(RATING_FILE, 'w') as f:
                json.dump(self.ratings, f, indent=4)
            logging.info(f"Elo ratings saved to {RATING_FILE}")
        except IOError as e:
            logging.error(f"Error: Could not save ratings file. Error: {e}")

    def get_rating(self, model_id: str) -> int:
        """Gets the rating for a model, returning the initial rating if not found."""
        return self.ratings.get(model_id, self.initial_rating)

    def get_all_ratings_sorted(self) -> list[tuple[str, int]]:
        """Returns all model ratings, sorted from highest to lowest."""
        return sorted(self.ratings.items(), key=lambda item: item[1], reverse=True)

    def _get_expected_score(self, rating_a: int, rating_b: int) -> tuple[float, float]:
        """
        Calculates the expected score for two players based on their ratings.
        """
        expected_a = 1 / (1 + math.pow(10, (rating_b - rating_a) / 400))
        expected_b = 1 - expected_a
        return expected_a, expected_b

    def update_ratings(self, model_a_id: str, model_b_id: str, outcome: str):
        """
        Updates the ratings of two models based on a match outcome and saves them.
        """
        rating_a = self.get_rating(model_a_id)
        rating_b = self.get_rating(model_b_id)

        expected_a, expected_b = self._get_expected_score(rating_a, rating_b)

        if outcome == "win_a":
            score_a, score_b = 1.0, 0.0
        elif outcome == "win_b":
            score_a, score_b = 0.0, 1.0
        elif outcome == "draw":
            score_a, score_b = 0.5, 0.5
        else:
            return # Invalid outcome

        new_rating_a = rating_a + self.k_factor * (score_a - expected_a)
        new_rating_b = rating_b + self.k_factor * (score_b - expected_b)

        self.ratings[model_a_id] = round(new_rating_a)
        self.ratings[model_b_id] = round(new_rating_b)
        
        logging.info(f"Ratings updated: {model_a_id}: {self.ratings[model_a_id]}, {model_b_id}: {self.ratings[model_b_id]}")
        self.save_ratings() # Automatically save after every update.


# Global instance to be used throughout the application
elo_system = EloRatingSystem()