"""
Adaptive Difficulty Engine — Synaptia
Dynamically adjusts puzzle difficulty based on real-time user performance
using a windowed Elo-inspired rating system.
"""

from __future__ import annotations

import logging
import math
from collections import deque
from datetime import datetime
from typing import Literal

logger = logging.getLogger(__name__)

# ── Types ─────────────────────────────────────────────────────────────────────

Difficulty = Literal["easy", "medium", "hard"]

# ── Constants ─────────────────────────────────────────────────────────────────

# Elo-style rating anchors per difficulty
DIFFICULTY_RATINGS: dict[str, int] = {
    "easy":   800,
    "medium": 1200,
    "hard":   1600,
}

STARTING_RATING        = 1000   # new user starting rating
K_FACTOR               = 32     # Elo K-factor (sensitivity)
WINDOW_SIZE            = 15     # rolling window of recent results
MIN_RATING             = 400
MAX_RATING             = 2000

# Thresholds for difficulty promotion/demotion
PROMOTE_THRESHOLD      = 0.70   # accuracy above this → promote
DEMOTE_THRESHOLD       = 0.35   # accuracy below this → demote
MIN_WINDOW_FOR_ADJUST  = 5      # need at least this many results to adjust


# ── DifficultyEngine ──────────────────────────────────────────────────────────

class DifficultyEngine:
    """
    Adaptive difficulty manager using an Elo-inspired rating system.

    Each user has a floating rating (400–2000). After every puzzle attempt,
    the rating updates based on whether the answer was correct and how many
    hints were used. The recommended difficulty is derived from the rating.

    Example usage:
        engine = DifficultyEngine()
        engine.record_result("user-1", difficulty="medium", correct=True, hints_used=0)
        rec = engine.recommend("user-1")
        # {"difficulty": "hard", "rating": 1215, "confidence": "medium"}
    """

    def __init__(self) -> None:
        # {user_id: current int rating}
        self._ratings: dict[str, int] = {}
        # {user_id: deque of result dicts}
        self._history: dict[str, deque] = {}

    # ── Public: recording ─────────────────────────────────────────────────────

    def record_result(
        self,
        user_id: str,
        difficulty: Difficulty,
        correct: bool,
        hints_used: int = 0,
        time_taken_s: float | None = None,
    ) -> dict:
        """
        Record a puzzle result and update the user's Elo rating.

        Returns the new rating snapshot dict.
        """
        if user_id not in self._ratings:
            self._ratings[user_id] = STARTING_RATING
            self._history[user_id] = deque(maxlen=WINDOW_SIZE)

        old_rating      = self._ratings[user_id]
        puzzle_rating   = DIFFICULTY_RATINGS.get(difficulty, DIFFICULTY_RATINGS["medium"])
        expected        = self._expected_score(old_rating, puzzle_rating)
        actual          = self._actual_score(correct, hints_used)
        delta           = round(K_FACTOR * (actual - expected))
        new_rating      = max(MIN_RATING, min(MAX_RATING, old_rating + delta))

        self._ratings[user_id] = new_rating
        self._history[user_id].append({
            "difficulty":  difficulty,
            "correct":     correct,
            "hints_used":  hints_used,
            "time_taken_s": time_taken_s,
            "rating_before": old_rating,
            "rating_after":  new_rating,
            "delta":        delta,
            "ts":          datetime.utcnow().isoformat(),
        })

        logger.debug(
            "[DifficultyEngine] user=%s %s→%s (Δ%+d) correct=%s hints=%d",
            user_id, old_rating, new_rating, delta, correct, hints_used,
        )
        return self._snapshot(user_id)

    # ── Public: recommendation ────────────────────────────────────────────────

    def recommend(self, user_id: str) -> dict:
        """
        Recommend the next puzzle difficulty and return confidence level.

        Returns dict with: difficulty, rating, confidence, reasoning.
        """
        rating     = self._ratings.get(user_id, STARTING_RATING)
        difficulty = self._rating_to_difficulty(rating)
        history    = list(self._history.get(user_id, []))
        window     = history[-WINDOW_SIZE:]

        confidence, reasoning = self._assess_confidence(window, rating)

        # Override with window-based rule if confidence warrants it
        if len(window) >= MIN_WINDOW_FOR_ADJUST:
            acc = sum(1 for r in window if r["correct"]) / len(window)
            if acc > PROMOTE_THRESHOLD and difficulty != "hard":
                difficulty = self._promote(difficulty)
                reasoning  = f"Window accuracy {acc:.0%} exceeds promote threshold — stepping up."
            elif acc < DEMOTE_THRESHOLD and difficulty != "easy":
                difficulty = self._demote(difficulty)
                reasoning  = f"Window accuracy {acc:.0%} below demote threshold — stepping down."

        return {
            "difficulty": difficulty,
            "rating":     rating,
            "confidence": confidence,
            "reasoning":  reasoning,
        }

    def get_rating(self, user_id: str) -> int:
        """Return the current Elo rating for a user."""
        return self._ratings.get(user_id, STARTING_RATING)

    def get_history(self, user_id: str, limit: int = 20) -> list[dict]:
        """Return the most recent `limit` rated results for a user."""
        history = list(self._history.get(user_id, []))
        return history[-limit:]

    def get_all_ratings(self) -> dict[str, int]:
        """Return a snapshot of all user ratings (for leaderboard use)."""
        return dict(self._ratings)

    # ── Private: Elo maths ────────────────────────────────────────────────────

    @staticmethod
    def _expected_score(player_rating: int, opponent_rating: int) -> float:
        """Standard Elo expected score formula."""
        return 1 / (1 + math.pow(10, (opponent_rating - player_rating) / 400))

    @staticmethod
    def _actual_score(correct: bool, hints_used: int) -> float:
        """
        Actual score with hint penalty.
          - Correct, 0 hints  → 1.0
          - Correct, 1 hint   → 0.8
          - Correct, 2+ hints → 0.6
          - Incorrect         → 0.0
        """
        if not correct:
            return 0.0
        if hints_used == 0:
            return 1.0
        if hints_used == 1:
            return 0.8
        return 0.6

    @staticmethod
    def _rating_to_difficulty(rating: int) -> Difficulty:
        if rating < 1000:
            return "easy"
        if rating < 1400:
            return "medium"
        return "hard"

    @staticmethod
    def _promote(difficulty: Difficulty) -> Difficulty:
        return {"easy": "medium", "medium": "hard"}.get(difficulty, difficulty)  # type: ignore[return-value]

    @staticmethod
    def _demote(difficulty: Difficulty) -> Difficulty:
        return {"hard": "medium", "medium": "easy"}.get(difficulty, difficulty)  # type: ignore[return-value]

    def _assess_confidence(self, window: list[dict], rating: int) -> tuple[str, str]:
        """Return (confidence_level, reasoning_string)."""
        n = len(window)
        if n < MIN_WINDOW_FOR_ADJUST:
            return "low", f"Only {n} data points — need {MIN_WINDOW_FOR_ADJUST} for reliable recommendation."
        if n < 10:
            return "medium", f"Based on {n} recent results (rating {rating})."
        return "high", f"Based on {n} recent results (rating {rating}) — strong signal."

    def _snapshot(self, user_id: str) -> dict:
        history = list(self._history[user_id])
        last    = history[-1] if history else {}
        return {
            "user_id":    user_id,
            "rating":     self._ratings[user_id],
            "delta":      last.get("delta", 0),
            "difficulty": self._rating_to_difficulty(self._ratings[user_id]),
            "results_logged": len(history),
        }

    # ── Utility: bulk seeding ─────────────────────────────────────────────────

    def seed_rating(self, user_id: str, rating: int) -> None:
        """
        Manually set a starting rating for a user (e.g. from a persisted DB).
        Clamps to [MIN_RATING, MAX_RATING].
        """
        self._ratings[user_id] = max(MIN_RATING, min(MAX_RATING, rating))
        if user_id not in self._history:
            self._history[user_id] = deque(maxlen=WINDOW_SIZE)
        logger.info("[DifficultyEngine] Seeded user=%s with rating=%d", user_id, self._ratings[user_id])
