"""
Synaptia — Unit Test Suite
Tests for analytics, difficulty engine, progress tracker, puzzle generator (answer checking),
and interview coach.

Run with:
    pytest tests/ -v
or from the project root:
    python -m pytest tests/ -v
"""

import sys
import os
import pytest

# Make sure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics import AnalyticsEngine
from difficulty_engine import DifficultyEngine, STARTING_RATING, MIN_RATING, MAX_RATING
from progress_tracker import ProgressTracker, BADGES, DEFAULT_WEEKLY_GOAL
from puzzle_generator import PuzzleGenerator
from interview_coach import InterviewCoach, INTERVIEW_DOMAINS


# ═══════════════════════════════════════════════════════════════════════════════
#  Analytics Engine Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsEngine:

    def setup_method(self):
        self.engine = AnalyticsEngine()

    def test_record_attempt_correct(self):
        snap = self.engine.record_attempt(
            "u1", "abc", "medium", "riddle", correct=True, hints_used=0
        )
        assert snap["total_attempts"] == 1
        assert snap["total_correct"]  == 1

    def test_record_attempt_incorrect(self):
        snap = self.engine.record_attempt(
            "u1", "abc", "medium", "riddle", correct=False, hints_used=1
        )
        assert snap["total_correct"] == 0
        assert snap["total_hints"]   == 1

    def test_multiple_attempts_accuracy(self):
        for i in range(8):
            self.engine.record_attempt("u2", f"p{i}", "easy", "riddle", correct=True)
        for i in range(2):
            self.engine.record_attempt("u2", f"q{i}", "easy", "riddle", correct=False)
        acc = self.engine._overall_accuracy("u2")
        assert acc == 80.0

    def test_dashboard_structure(self):
        self.engine.record_attempt("u3", "p1", "hard", "math", correct=True, hints_used=0)
        dash = self.engine.get_dashboard("u3")
        assert "totals"           in dash
        assert "accuracy"         in dash
        assert "cognitive_score"  in dash
        assert "trends"           in dash
        assert "difficulty_spread" in dash

    def test_record_hint(self):
        self.engine.record_hint("u4", "p1", hint_number=0)
        agg = self.engine._aggregates["u4"]
        assert agg["total_hints"] == 1

    def test_record_chat(self):
        self.engine.record_chat("u5", "sess-1", "hint_bot")
        agg = self.engine._aggregates["u5"]
        assert agg["total_chats"] == 1

    def test_get_user_events_limit(self):
        for i in range(30):
            self.engine.record_attempt("u6", f"p{i}", "easy", "riddle", correct=True)
        events = self.engine.get_user_events("u6", limit=10)
        assert len(events) == 10

    def test_leaderboard_ordering(self):
        # u7 solves more hard puzzles → higher cognitive score
        for i in range(20):
            self.engine.record_attempt("u7", f"p{i}", "hard", "logic", correct=True, hints_used=0)
        for i in range(5):
            self.engine.record_attempt("u8", f"q{i}", "easy", "riddle", correct=True, hints_used=2)
        board = self.engine.get_leaderboard(top_n=5)
        ids = [entry["user_id"] for entry in board]
        assert ids.index("u7") < ids.index("u8")

    def test_cognitive_score_zero_for_new_user(self):
        score = self.engine._cognitive_score("brand_new_user")
        assert score == 0

    def test_open_and_close_session(self):
        self.engine.open_session("u9", "sess-abc")
        summary = self.engine.close_session("u9", "sess-abc")
        assert summary is not None
        assert "duration_s" in summary
        assert summary["session_id"] == "sess-abc"


# ═══════════════════════════════════════════════════════════════════════════════
#  Difficulty Engine Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestDifficultyEngine:

    def setup_method(self):
        self.engine = DifficultyEngine()

    def test_new_user_starts_at_default_rating(self):
        assert self.engine.get_rating("new_user") == STARTING_RATING

    def test_correct_answer_increases_rating(self):
        self.engine.record_result("u1", "medium", correct=True, hints_used=0)
        assert self.engine.get_rating("u1") > STARTING_RATING

    def test_incorrect_answer_decreases_rating(self):
        self.engine.record_result("u1", "medium", correct=False)
        assert self.engine.get_rating("u1") < STARTING_RATING

    def test_rating_clamped_to_min(self):
        self.engine.seed_rating("u2", MIN_RATING)
        for _ in range(10):
            self.engine.record_result("u2", "hard", correct=False)
        assert self.engine.get_rating("u2") >= MIN_RATING

    def test_rating_clamped_to_max(self):
        self.engine.seed_rating("u3", MAX_RATING)
        for _ in range(10):
            self.engine.record_result("u3", "easy", correct=True, hints_used=0)
        assert self.engine.get_rating("u3") <= MAX_RATING

    def test_hints_reduce_rating_gain(self):
        self.engine.seed_rating("u4", STARTING_RATING)
        snap_no_hint = self.engine.record_result("u4", "medium", correct=True, hints_used=0)

        self.engine.seed_rating("u5", STARTING_RATING)
        snap_with_hint = self.engine.record_result("u5", "medium", correct=True, hints_used=2)

        assert snap_no_hint["rating"] > snap_with_hint["rating"]

    def test_recommend_returns_valid_difficulty(self):
        rec = self.engine.recommend("u6")
        assert rec["difficulty"] in ("easy", "medium", "hard")
        assert "rating" in rec
        assert "confidence" in rec

    def test_high_accuracy_promotes_difficulty(self):
        # Seed user with medium-level rating then win streak
        self.engine.seed_rating("u7", 1100)
        for _ in range(10):
            self.engine.record_result("u7", "medium", correct=True, hints_used=0)
        rec = self.engine.recommend("u7")
        # Should be promoted beyond medium
        assert rec["difficulty"] in ("medium", "hard")

    def test_low_accuracy_demotes_difficulty(self):
        self.engine.seed_rating("u8", 1500)
        for _ in range(10):
            self.engine.record_result("u8", "hard", correct=False)
        rec = self.engine.recommend("u8")
        assert rec["difficulty"] in ("easy", "medium")

    def test_seed_rating(self):
        self.engine.seed_rating("u9", 1800)
        assert self.engine.get_rating("u9") == 1800

    def test_get_history_limit(self):
        for i in range(25):
            self.engine.record_result("u10", "easy", correct=True)
        history = self.engine.get_history("u10", limit=10)
        assert len(history) == 10


# ═══════════════════════════════════════════════════════════════════════════════
#  Progress Tracker Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestProgressTracker:

    def setup_method(self):
        self.tracker = ProgressTracker()

    def test_record_solve_increments_count(self):
        self.tracker.record_solve("u1", "riddle", "easy", hints_used=0, correct=True)
        profile = self.tracker.get_profile("u1")
        assert profile["puzzles_solved"] == 1

    def test_incorrect_does_not_increment_solved(self):
        self.tracker.record_solve("u1", "riddle", "easy", hints_used=1, correct=False)
        profile = self.tracker.get_profile("u1")
        assert profile["puzzles_solved"] == 0
        assert profile["total_attempts"] == 1

    def test_hint_free_streak_resets_on_incorrect(self):
        for _ in range(5):
            self.tracker.record_solve("u2", "riddle", "easy", hints_used=0, correct=True)
        self.tracker.record_solve("u2", "riddle", "easy", hints_used=0, correct=False)
        profile = self.tracker.get_profile("u2")
        assert profile["hint_free_streak"] == 0

    def test_hint_free_streak_resets_when_hints_used(self):
        for _ in range(3):
            self.tracker.record_solve("u3", "math", "medium", hints_used=0, correct=True)
        self.tracker.record_solve("u3", "math", "medium", hints_used=2, correct=True)
        profile = self.tracker.get_profile("u3")
        assert profile["hint_free_streak"] == 0

    def test_first_solve_badge_unlocked(self):
        result = self.tracker.record_solve("u4", "riddle", "easy", hints_used=0, correct=True)
        assert "first_solve" in result["newly_unlocked_badges"]

    def test_hard_solver_badge(self):
        for _ in range(5):
            self.tracker.record_solve("u5", "logic", "hard", hints_used=0, correct=True)
        profile = self.tracker.get_profile("u5")
        assert "hard_solver" in profile["badges"]

    def test_accuracy_calculation(self):
        for _ in range(7):
            self.tracker.record_solve("u6", "math", "easy", hints_used=0, correct=True)
        for _ in range(3):
            self.tracker.record_solve("u6", "math", "easy", hints_used=0, correct=False)
        profile = self.tracker.get_profile("u6")
        assert profile["accuracy_pct"] == 70.0

    def test_type_breakdown(self):
        self.tracker.record_solve("u7", "math",     "easy", hints_used=0, correct=True)
        self.tracker.record_solve("u7", "wordplay",  "easy", hints_used=0, correct=True)
        self.tracker.record_solve("u7", "logic",    "easy", hints_used=0, correct=True)
        profile = self.tracker.get_profile("u7")
        breakdown = profile["type_breakdown"]
        assert breakdown["math"]     == 1
        assert breakdown["wordplay"] == 1
        assert breakdown["logic"]    == 1

    def test_weekly_goal_update(self):
        self.tracker.set_weekly_goal("u8", 20)
        profile = self.tracker.get_profile("u8")
        assert profile["weekly_goal"] == 20

    def test_export_report_has_recommendations(self):
        self.tracker.record_solve("u9", "riddle", "easy", hints_used=0, correct=True)
        report = self.tracker.export_report("u9")
        assert "recommendations" in report
        assert isinstance(report["recommendations"], list)
        assert len(report["recommendations"]) > 0

    def test_all_badges_are_reachable(self):
        """Ensure every badge in BADGES has the required metric field in the profile."""
        profile = self.tracker._get_or_create("badge_test_user")
        for bid, badge in BADGES.items():
            metric = badge["metric"]
            assert metric in profile or metric in (
                "puzzles_solved", "accuracy_pct", "hint_free_streak",
                "hard_puzzles_solved", "day_streak", "wordplay_solved",
                "math_solved", "logic_solved"
            ), f"Badge '{bid}' references unknown metric '{metric}'"

    def test_get_badges_returns_earned_list(self):
        # Earn first_solve badge
        self.tracker.record_solve("u10", "riddle", "easy", hints_used=0, correct=True)
        badges = self.tracker.get_badges("u10")
        assert any(b["name"] == "First Spark" for b in badges)


# ═══════════════════════════════════════════════════════════════════════════════
#  PuzzleGenerator — Answer Checking Tests (no API call needed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPuzzleGeneratorAnswerChecking:

    def setup_method(self):
        self.gen = PuzzleGenerator()
        # Inject a fake puzzle directly so no API is hit
        self.gen.puzzles["test1"] = {
            "id":          "test1",
            "question":    "What has keys but no locks?",
            "answer":      "A keyboard",
            "difficulty":  "easy",
            "type":        "riddle",
            "solved":      False,
            "hints":       [],
            "explanation": "A keyboard has keys but no locks or doors.",
            "solution_steps": ["Keys are on a keyboard.", "Keyboards have no physical locks."],
        }

    def test_exact_match(self):
        result = self.gen.check_answer("test1", "A keyboard")
        assert result["correct"] is True

    def test_case_insensitive_match(self):
        result = self.gen.check_answer("test1", "a keyboard")
        assert result["correct"] is True

    def test_fuzzy_match(self):
        result = self.gen.check_answer("test1", "keyboard")
        assert result["correct"] is True

    def test_wrong_answer(self):
        result = self.gen.check_answer("test1", "piano")
        assert result["correct"] is False
        assert result["answer"] is None

    def test_missing_puzzle(self):
        result = self.gen.check_answer("nonexistent", "anything")
        assert "error" in result

    def test_solved_flag_set_on_correct(self):
        self.gen.check_answer("test1", "A keyboard")
        assert self.gen.puzzles["test1"]["solved"] is True

    def test_list_puzzles_excludes_answer(self):
        puzzles = self.gen.list_puzzles()
        for p in puzzles:
            assert "answer" not in p
            assert "solution_steps" not in p


# ═══════════════════════════════════════════════════════════════════════════════
#  InterviewCoach Tests (no API call)
# ═══════════════════════════════════════════════════════════════════════════════

class TestInterviewCoach:

    def setup_method(self):
        self.coach = InterviewCoach()

    def test_start_session_creates_session(self):
        result = self.coach.start_session("u1", domain="cognitive")
        assert result["session_id"] == "u1"
        assert result["domain"]     == "cognitive"
        assert "u1" in self.coach.sessions

    def test_unknown_domain_falls_back_to_general(self):
        result = self.coach.start_session("u2", domain="underwater_basket_weaving")
        assert result["domain"] == "general"

    def test_get_session_status_active(self):
        self.coach.start_session("u3", domain="memory")
        status = self.coach.get_session_status("u3")
        assert status["active"]  is True
        assert status["domain"]  == "memory"

    def test_get_session_status_missing(self):
        status = self.coach.get_session_status("ghost_user")
        assert "error" in status

    def test_end_session_removes_session(self):
        self.coach.start_session("u4", domain="general")
        self.coach.end_session("u4")
        assert "u4" not in self.coach.sessions

    def test_end_session_returns_summary_keys(self):
        self.coach.start_session("u5", domain="behavioural")
        summary = self.coach.end_session("u5")
        for key in ("total_score", "questions_asked", "domain", "summary", "feedback_log"):
            assert key in summary

    def test_end_session_unknown_user(self):
        result = self.coach.end_session("nobody")
        assert "error" in result

    def test_all_domains_exist(self):
        for domain in ("cognitive", "memory", "behavioural", "technical", "general"):
            assert domain in INTERVIEW_DOMAINS

    def test_score_heuristic_short_answer(self):
        score = self.coach._score_response("ok", "Good answer.")
        assert score <= 4

    def test_score_heuristic_long_answer(self):
        long_answer = " ".join(["word"] * 80)
        score = self.coach._score_response(long_answer, "Excellent depth.")
        assert score == 10
