"""
Progress Tracker — Synaptia
Maintains per-user cognitive progress profiles, milestone badges,
weekly goal tracking, and exportable progress reports.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, date
from typing import Optional

logger = logging.getLogger(__name__)

# ── Badge definitions ─────────────────────────────────────────────────────────

BADGES: dict[str, dict] = {
    "first_solve": {
        "name":        "First Spark",
        "description": "Solved your very first puzzle.",
        "icon":        "⚡",
        "threshold":   1,
        "metric":      "puzzles_solved",
    },
    "ten_puzzles": {
        "name":        "Getting Started",
        "description": "Solved 10 puzzles.",
        "icon":        "🔟",
        "threshold":   10,
        "metric":      "puzzles_solved",
    },
    "fifty_puzzles": {
        "name":        "Consistent Mind",
        "description": "Solved 50 puzzles.",
        "icon":        "🧠",
        "threshold":   50,
        "metric":      "puzzles_solved",
    },
    "century": {
        "name":        "Century Club",
        "description": "Solved 100 puzzles.",
        "icon":        "💯",
        "threshold":   100,
        "metric":      "puzzles_solved",
    },
    "sharp_mind": {
        "name":        "Sharp Mind",
        "description": "Achieved 80%+ accuracy over 20+ puzzles.",
        "icon":        "🎯",
        "threshold":   80,
        "metric":      "accuracy_pct",
        "min_attempts": 20,
    },
    "no_hints": {
        "name":        "Unaided",
        "description": "Solved 10 puzzles in a row without hints.",
        "icon":        "🏆",
        "threshold":   10,
        "metric":      "hint_free_streak",
    },
    "hard_solver": {
        "name":        "Hard Mode",
        "description": "Solved 5 hard-difficulty puzzles.",
        "icon":        "🔥",
        "threshold":   5,
        "metric":      "hard_puzzles_solved",
    },
    "streak_3": {
        "name":        "On a Roll",
        "description": "3-day active streak.",
        "icon":        "🔥",
        "threshold":   3,
        "metric":      "day_streak",
    },
    "streak_7": {
        "name":        "Dedicated",
        "description": "7-day active streak.",
        "icon":        "🌟",
        "threshold":   7,
        "metric":      "day_streak",
    },
    "wordplay_master": {
        "name":        "Wordsmith",
        "description": "Solved 10 wordplay puzzles.",
        "icon":        "📝",
        "threshold":   10,
        "metric":      "wordplay_solved",
    },
    "math_wizard": {
        "name":        "Math Wizard",
        "description": "Solved 10 math puzzles.",
        "icon":        "🔢",
        "threshold":   10,
        "metric":      "math_solved",
    },
    "logic_lord": {
        "name":        "Logic Lord",
        "description": "Solved 10 logic puzzles.",
        "icon":        "♟️",
        "threshold":   10,
        "metric":      "logic_solved",
    },
}

# ── Weekly goal defaults ──────────────────────────────────────────────────────

DEFAULT_WEEKLY_GOAL = 15   # puzzles per week


# ── ProgressTracker ───────────────────────────────────────────────────────────

class ProgressTracker:
    """
    Per-user cognitive progress profile manager.

    Tracks:
    - Cumulative solve counts by type and difficulty
    - Badge / achievement unlocks
    - Weekly puzzle goals with progress %
    - Cognitive improvement trend (accuracy week-over-week)
    - Exportable progress snapshot

    Example usage:
        tracker = ProgressTracker()
        tracker.record_solve("user-1", puzzle_type="math", difficulty="hard",
                             hints_used=0, correct=True)
        profile = tracker.get_profile("user-1")
        report  = tracker.export_report("user-1")
    """

    def __init__(self) -> None:
        self._profiles: dict[str, dict] = {}

    # ── Public: recording ─────────────────────────────────────────────────────

    def record_solve(
        self,
        user_id: str,
        puzzle_type: str,
        difficulty: str,
        hints_used: int,
        correct: bool,
        time_taken_s: Optional[float] = None,
    ) -> dict:
        """
        Record a puzzle attempt and update all progress metrics.

        Returns the list of newly unlocked badge IDs (may be empty).
        """
        profile = self._get_or_create(user_id)
        profile["total_attempts"] += 1

        if correct:
            profile["puzzles_solved"] += 1
            profile[f"{puzzle_type}_solved"] = profile.get(f"{puzzle_type}_solved", 0) + 1
            if difficulty == "hard":
                profile["hard_puzzles_solved"] += 1
            if hints_used == 0:
                profile["hint_free_streak"] += 1
            else:
                profile["hint_free_streak"] = 0
        else:
            profile["hint_free_streak"] = 0

        profile["total_hints_used"] += hints_used
        profile["weekly_solved_this_week"] = self._this_week_count(profile)
        profile["last_active"] = datetime.utcnow().isoformat()

        # Append to solve log for weekly/trend calculations
        profile["solve_log"].append({
            "type":        puzzle_type,
            "difficulty":  difficulty,
            "correct":     correct,
            "hints_used":  hints_used,
            "time_taken_s": time_taken_s,
            "date":        date.today().isoformat(),
        })
        # Keep log bounded to 365 days of entries
        if len(profile["solve_log"]) > 365 * 3:
            profile["solve_log"] = profile["solve_log"][-365 * 3:]

        # Accuracy recalculation
        if profile["total_attempts"] > 0:
            profile["accuracy_pct"] = round(
                profile["puzzles_solved"] / profile["total_attempts"] * 100, 1
            )

        newly_unlocked = self._evaluate_badges(user_id, profile)
        return {"newly_unlocked_badges": newly_unlocked}

    def set_weekly_goal(self, user_id: str, goal: int) -> None:
        """Set or update the user's weekly puzzle goal."""
        profile = self._get_or_create(user_id)
        profile["weekly_goal"] = max(1, int(goal))
        logger.info("[ProgressTracker] user=%s weekly_goal=%d", user_id, profile["weekly_goal"])

    def update_streak(self, user_id: str, streak_days: int) -> list[str]:
        """
        Sync the day streak from the AnalyticsEngine and evaluate streak badges.
        Returns list of newly unlocked badge IDs.
        """
        profile = self._get_or_create(user_id)
        profile["day_streak"] = streak_days
        return self._evaluate_badges(user_id, profile)

    # ── Public: reporting ─────────────────────────────────────────────────────

    def get_profile(self, user_id: str) -> dict:
        """Return the full progress profile for a user."""
        profile = self._get_or_create(user_id)
        return {
            "user_id":             user_id,
            "puzzles_solved":      profile["puzzles_solved"],
            "total_attempts":      profile["total_attempts"],
            "accuracy_pct":        profile["accuracy_pct"],
            "hard_puzzles_solved": profile["hard_puzzles_solved"],
            "hint_free_streak":    profile["hint_free_streak"],
            "day_streak":          profile["day_streak"],
            "total_hints_used":    profile["total_hints_used"],
            "type_breakdown":      self._type_breakdown(profile),
            "weekly_goal":         profile["weekly_goal"],
            "weekly_progress":     self._weekly_progress(profile),
            "badges":              profile["earned_badges"],
            "badge_details":       [BADGES[b] for b in profile["earned_badges"] if b in BADGES],
            "cognitive_trend":     self._week_over_week_trend(profile),
            "last_active":         profile.get("last_active"),
        }

    def get_badges(self, user_id: str) -> list[dict]:
        """Return all earned badge details for a user."""
        profile = self._get_or_create(user_id)
        return [
            {"id": bid, **BADGES[bid]}
            for bid in profile["earned_badges"]
            if bid in BADGES
        ]

    def export_report(self, user_id: str) -> dict:
        """
        Export a full progress report suitable for rendering or saving.
        Includes all metrics, history summary, and recommendations.
        """
        profile = self._get_or_create(user_id)
        full    = self.get_profile(user_id)
        full["recommendations"] = self._recommendations(profile)
        full["exported_at"]     = datetime.utcnow().isoformat()
        full["total_badges_available"] = len(BADGES)
        full["completion_pct"] = round(
            len(profile["earned_badges"]) / len(BADGES) * 100, 1
        )
        return full

    # ── Private: helpers ──────────────────────────────────────────────────────

    def _get_or_create(self, user_id: str) -> dict:
        if user_id not in self._profiles:
            self._profiles[user_id] = {
                "puzzles_solved":       0,
                "total_attempts":       0,
                "accuracy_pct":         0.0,
                "hard_puzzles_solved":  0,
                "hint_free_streak":     0,
                "day_streak":           0,
                "total_hints_used":     0,
                "riddle_solved":        0,
                "math_solved":          0,
                "logic_solved":         0,
                "wordplay_solved":      0,
                "trivia_solved":        0,
                "weekly_goal":          DEFAULT_WEEKLY_GOAL,
                "weekly_solved_this_week": 0,
                "earned_badges":        [],
                "solve_log":            [],
                "last_active":          None,
            }
        return self._profiles[user_id]

    def _evaluate_badges(self, user_id: str, profile: dict) -> list[str]:
        """Check all badge conditions and unlock newly earned ones. Returns new IDs."""
        newly_unlocked: list[str] = []
        earned = set(profile["earned_badges"])

        for badge_id, badge in BADGES.items():
            if badge_id in earned:
                continue
            metric    = badge["metric"]
            threshold = badge["threshold"]
            value     = profile.get(metric, 0)
            min_att   = badge.get("min_attempts", 0)

            if value >= threshold and profile["total_attempts"] >= min_att:
                profile["earned_badges"].append(badge_id)
                newly_unlocked.append(badge_id)
                logger.info("[ProgressTracker] user=%s earned badge: %s (%s)", user_id, badge_id, badge["name"])

        return newly_unlocked

    def _type_breakdown(self, profile: dict) -> dict:
        return {
            t: profile.get(f"{t}_solved", 0)
            for t in ("riddle", "math", "logic", "wordplay", "trivia")
        }

    def _this_week_count(self, profile: dict) -> int:
        """Count solves from the current ISO week."""
        today    = date.today()
        week_start = today - timedelta(days=today.weekday())
        return sum(
            1 for e in profile["solve_log"]
            if e.get("correct") and
            date.fromisoformat(e["date"]) >= week_start
        )

    def _weekly_progress(self, profile: dict) -> dict:
        done  = self._this_week_count(profile)
        goal  = profile["weekly_goal"]
        return {
            "solved_this_week": done,
            "goal":             goal,
            "pct":              round(done / goal * 100, 1) if goal else 0,
            "remaining":        max(0, goal - done),
        }

    def _week_over_week_trend(self, profile: dict) -> dict:
        """Compare accuracy this week vs last week."""
        today      = date.today()
        this_start = today - timedelta(days=today.weekday())
        last_start = this_start - timedelta(weeks=1)

        def _acc(log_slice: list) -> Optional[float]:
            if not log_slice:
                return None
            return round(sum(1 for e in log_slice if e["correct"]) / len(log_slice) * 100, 1)

        this_week = [e for e in profile["solve_log"] if date.fromisoformat(e["date"]) >= this_start]
        last_week = [e for e in profile["solve_log"]
                     if last_start <= date.fromisoformat(e["date"]) < this_start]

        this_acc = _acc(this_week)
        last_acc = _acc(last_week)
        delta    = round(this_acc - last_acc, 1) if (this_acc is not None and last_acc is not None) else None

        return {
            "this_week_accuracy": this_acc,
            "last_week_accuracy": last_acc,
            "delta":              delta,
            "direction":          ("up" if delta and delta > 0 else "down" if delta and delta < 0 else "flat"),
        }

    def _recommendations(self, profile: dict) -> list[str]:
        """Generate personalised improvement recommendations."""
        recs: list[str] = []

        if profile["accuracy_pct"] < 50 and profile["total_attempts"] >= 5:
            recs.append("Try easier puzzles to build confidence before moving to harder ones.")
        if profile["total_hints_used"] > profile["puzzles_solved"] * 2:
            recs.append("Challenge yourself to use fewer hints — try solving with just one clue.")
        if profile["hard_puzzles_solved"] == 0 and profile["puzzles_solved"] >= 20:
            recs.append("You're ready to try Hard difficulty — push your limits!")
        if profile.get("math_solved", 0) == 0 and profile["puzzles_solved"] >= 10:
            recs.append("You haven't tried any Math puzzles yet — they're great for logical reasoning.")
        if profile["day_streak"] == 0:
            recs.append("Start a daily streak! Even 5 minutes a day builds lasting cognitive habits.")
        if not recs:
            recs.append("Excellent progress — keep going and unlock more badges!")
        return recs
