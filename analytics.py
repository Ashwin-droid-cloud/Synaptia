"""
Analytics Engine — Synaptia
Tracks user performance metrics, session history, and cognitive load trends.
All data is held in-memory; swap self._store for a DB adapter in production.
"""

from __future__ import annotations

import logging
import statistics
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_EVENTS_PER_USER = 500   # rolling window cap
TREND_WINDOW        = 10    # last N puzzles used for trend calculations
STREAK_GAP_HOURS    = 26    # hours within which a new session extends the streak


# ── AnalyticsEngine ───────────────────────────────────────────────────────────

class AnalyticsEngine:
    """
    Central analytics store for Synaptia.

    Tracks:
    - Per-user event log (puzzle attempts, hints, chat messages)
    - Session-level summaries (duration, accuracy, hints/puzzle)
    - Trend metrics (rolling accuracy, difficulty progression)
    - Cognitive engagement score (derived composite metric)
    - Streak tracking (consecutive active days)

    Example usage:
        engine = AnalyticsEngine()
        engine.record_attempt("user-1", puzzle_id="abc123", difficulty="medium",
                              puzzle_type="riddle", correct=True, hints_used=1,
                              time_taken_s=45)
        dashboard = engine.get_dashboard("user-1")
    """

    def __init__(self) -> None:
        # {user_id: deque of event dicts}
        self._events: dict[str, deque] = defaultdict(lambda: deque(maxlen=MAX_EVENTS_PER_USER))
        # {user_id: list of session summary dicts}
        self._sessions: dict[str, list] = defaultdict(list)
        # {user_id: dict of aggregate counters}
        self._aggregates: dict[str, dict] = defaultdict(self._empty_aggregate)

    # ── Public: recording ─────────────────────────────────────────────────────

    def record_attempt(
        self,
        user_id: str,
        puzzle_id: str,
        difficulty: str,
        puzzle_type: str,
        correct: bool,
        hints_used: int = 0,
        time_taken_s: Optional[float] = None,
    ) -> dict:
        """
        Record a single puzzle attempt event.

        Returns the updated aggregate snapshot for the user.
        """
        event = {
            "kind":         "attempt",
            "puzzle_id":    puzzle_id,
            "difficulty":   difficulty,
            "puzzle_type":  puzzle_type,
            "correct":      correct,
            "hints_used":   hints_used,
            "time_taken_s": time_taken_s,
            "ts":           datetime.utcnow().isoformat(),
        }
        self._events[user_id].append(event)
        self._update_aggregates(user_id, event)
        logger.debug("[Analytics] Recorded attempt for user=%s puzzle=%s correct=%s", user_id, puzzle_id, correct)
        return self._aggregates[user_id].copy()

    def record_hint(self, user_id: str, puzzle_id: str, hint_number: int) -> None:
        """Record a hint request event."""
        event = {
            "kind":       "hint",
            "puzzle_id":  puzzle_id,
            "hint_number": hint_number,
            "ts":         datetime.utcnow().isoformat(),
        }
        self._events[user_id].append(event)
        self._aggregates[user_id]["total_hints"] += 1

    def record_chat(self, user_id: str, session_id: str, chat_mode: str) -> None:
        """Record a chat interaction event."""
        event = {
            "kind":       "chat",
            "session_id": session_id,
            "chat_mode":  chat_mode,
            "ts":         datetime.utcnow().isoformat(),
        }
        self._events[user_id].append(event)
        self._aggregates[user_id]["total_chats"] += 1

    def open_session(self, user_id: str, session_id: str) -> None:
        """Mark the start of a new app session."""
        self._sessions[user_id].append({
            "session_id": session_id,
            "started_at": datetime.utcnow().isoformat(),
            "ended_at":   None,
            "attempts":   0,
            "correct":    0,
        })
        self._update_streak(user_id)

    def close_session(self, user_id: str, session_id: str) -> Optional[dict]:
        """Mark the end of a session and return its summary."""
        for s in reversed(self._sessions[user_id]):
            if s["session_id"] == session_id and s["ended_at"] is None:
                s["ended_at"] = datetime.utcnow().isoformat()
                started = datetime.fromisoformat(s["started_at"])
                ended   = datetime.fromisoformat(s["ended_at"])
                s["duration_s"] = (ended - started).total_seconds()
                logger.info("[Analytics] Closed session=%s duration=%.0fs", session_id, s["duration_s"])
                return s
        return None

    # ── Public: reporting ─────────────────────────────────────────────────────

    def get_dashboard(self, user_id: str) -> dict:
        """
        Return a comprehensive analytics dashboard dict for the given user.

        Keys: totals, accuracy, trends, streaks, cognitive_score, top_types.
        """
        agg      = self._aggregates[user_id]
        attempts = self._attempt_events(user_id)

        return {
            "user_id":         user_id,
            "totals": {
                "puzzles_attempted": agg["total_attempts"],
                "puzzles_solved":    agg["total_correct"],
                "hints_requested":   agg["total_hints"],
                "chat_interactions": agg["total_chats"],
            },
            "accuracy":           self._overall_accuracy(user_id),
            "trends":             self._rolling_trend(user_id, TREND_WINDOW),
            "difficulty_spread":  self._difficulty_spread(attempts),
            "type_spread":        self._type_spread(attempts),
            "top_type":           self._best_type(attempts),
            "avg_time_s":         self._avg_time(attempts),
            "avg_hints_per_puzzle": self._avg_hints(attempts),
            "streak_days":        agg.get("streak_days", 0),
            "cognitive_score":    self._cognitive_score(user_id),
            "generated_at":       datetime.utcnow().isoformat(),
        }

    def get_leaderboard(self, top_n: int = 10) -> list[dict]:
        """
        Return top_n users ranked by cognitive score.
        """
        scores = []
        for uid in self._aggregates:
            scores.append({
                "user_id":        uid,
                "cognitive_score": self._cognitive_score(uid),
                "puzzles_solved":  self._aggregates[uid]["total_correct"],
                "accuracy":        self._overall_accuracy(uid),
            })
        scores.sort(key=lambda x: x["cognitive_score"], reverse=True)
        return scores[:top_n]

    def get_user_events(self, user_id: str, limit: int = 50) -> list[dict]:
        """Return the most recent `limit` events for a user."""
        events = list(self._events[user_id])
        return events[-limit:]

    # ── Private: aggregation ──────────────────────────────────────────────────

    @staticmethod
    def _empty_aggregate() -> dict:
        return {
            "total_attempts": 0,
            "total_correct":  0,
            "total_hints":    0,
            "total_chats":    0,
            "streak_days":    0,
            "last_active":    None,
        }

    def _update_aggregates(self, user_id: str, event: dict) -> None:
        agg = self._aggregates[user_id]
        agg["total_attempts"] += 1
        if event.get("correct"):
            agg["total_correct"] += 1
        agg["total_hints"]   += event.get("hints_used", 0)
        agg["last_active"]    = event["ts"]

    def _update_streak(self, user_id: str) -> None:
        agg         = self._aggregates[user_id]
        last_active = agg.get("last_active")
        now         = datetime.utcnow()

        if last_active:
            last_dt = datetime.fromisoformat(last_active)
            gap     = (now - last_dt).total_seconds() / 3600
            if gap <= STREAK_GAP_HOURS:
                agg["streak_days"] = agg.get("streak_days", 0) + 1
            else:
                agg["streak_days"] = 1
        else:
            agg["streak_days"] = 1

        agg["last_active"] = now.isoformat()

    # ── Private: metrics ──────────────────────────────────────────────────────

    def _attempt_events(self, user_id: str) -> list[dict]:
        return [e for e in self._events[user_id] if e["kind"] == "attempt"]

    def _overall_accuracy(self, user_id: str) -> float:
        agg = self._aggregates[user_id]
        if agg["total_attempts"] == 0:
            return 0.0
        return round(agg["total_correct"] / agg["total_attempts"] * 100, 1)

    def _rolling_trend(self, user_id: str, window: int) -> dict:
        """Accuracy trend over the last `window` attempts."""
        recent = self._attempt_events(user_id)[-window:]
        if not recent:
            return {"window": window, "accuracy": 0.0, "delta": 0.0}
        acc = sum(1 for e in recent if e["correct"]) / len(recent) * 100
        prior = self._attempt_events(user_id)[-(window * 2):-window]
        if prior:
            prior_acc = sum(1 for e in prior if e["correct"]) / len(prior) * 100
            delta = round(acc - prior_acc, 1)
        else:
            delta = 0.0
        return {"window": window, "accuracy": round(acc, 1), "delta": delta}

    def _difficulty_spread(self, attempts: list[dict]) -> dict:
        spread: dict[str, dict] = {}
        for e in attempts:
            d = e.get("difficulty", "unknown")
            if d not in spread:
                spread[d] = {"attempted": 0, "correct": 0}
            spread[d]["attempted"] += 1
            if e["correct"]:
                spread[d]["correct"] += 1
        for d, v in spread.items():
            v["accuracy"] = round(v["correct"] / v["attempted"] * 100, 1) if v["attempted"] else 0.0
        return spread

    def _type_spread(self, attempts: list[dict]) -> dict:
        spread: dict[str, dict] = {}
        for e in attempts:
            t = e.get("puzzle_type", "unknown")
            if t not in spread:
                spread[t] = {"attempted": 0, "correct": 0}
            spread[t]["attempted"] += 1
            if e["correct"]:
                spread[t]["correct"] += 1
        for t, v in spread.items():
            v["accuracy"] = round(v["correct"] / v["attempted"] * 100, 1) if v["attempted"] else 0.0
        return spread

    def _best_type(self, attempts: list[dict]) -> Optional[str]:
        spread = self._type_spread(attempts)
        if not spread:
            return None
        return max(spread, key=lambda t: spread[t]["accuracy"])

    def _avg_time(self, attempts: list[dict]) -> Optional[float]:
        times = [e["time_taken_s"] for e in attempts if e.get("time_taken_s") is not None]
        return round(statistics.mean(times), 1) if times else None

    def _avg_hints(self, attempts: list[dict]) -> float:
        if not attempts:
            return 0.0
        return round(sum(e.get("hints_used", 0) for e in attempts) / len(attempts), 2)

    def _cognitive_score(self, user_id: str) -> int:
        """
        Composite cognitive engagement score (0–1000).

        Formula weights:
          - Accuracy       : 40%
          - Volume         : 20%  (capped at 100 puzzles)
          - Hint efficiency : 20%  (fewer hints = higher score)
          - Streak bonus   : 10%
          - Hard difficulty : 10%
        """
        agg      = self._aggregates[user_id]
        attempts = self._attempt_events(user_id)
        if not attempts:
            return 0

        accuracy_score  = self._overall_accuracy(user_id) / 100 * 400
        volume_score    = min(agg["total_attempts"] / 100, 1.0) * 200
        hint_ratio      = self._avg_hints(attempts)
        hint_score      = max(0, 1 - hint_ratio / 3) * 200
        streak_score    = min(agg.get("streak_days", 0) / 30, 1.0) * 100
        hard_attempts   = sum(1 for e in attempts if e.get("difficulty") == "hard" and e["correct"])
        hard_score      = min(hard_attempts / 20, 1.0) * 100

        total = accuracy_score + volume_score + hint_score + streak_score + hard_score
        return int(round(total))
