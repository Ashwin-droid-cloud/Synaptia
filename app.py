"""
Synaptia — Flask Application
Main server with API routes for exercise generation, hints, chat, answer checking,
analytics, adaptive difficulty, progress tracking, and interview coaching.
Powered by the Groq API (groq.com) with an AI cross-validation layer to prevent hallucinations.
"""

from flask import Flask, render_template, request, jsonify, redirect
from flask_cors import CORS
from config import config
from puzzle_generator import PuzzleGenerator
from hint_provider import HintProvider
from analytics import AnalyticsEngine
from difficulty_engine import DifficultyEngine
from progress_tracker import ProgressTracker
from interview_coach import InterviewCoach
import os
import logging
from datetime import datetime

# Configure logging so model rotation events appear in the console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# ============== APP SETUP ==============

app = Flask(__name__)
CORS(app)

config_name = os.getenv("FLASK_ENV", "development")
app.config.from_object(config[config_name])
app.config["SESSION_TYPE"] = "filesystem"

# Initialize modules
puzzle_gen       = PuzzleGenerator()
hint_provider    = HintProvider()
analytics_engine = AnalyticsEngine()
difficulty_engine = DifficultyEngine()
progress_tracker = ProgressTracker()
interview_coach  = InterviewCoach()

# In-memory session tracking
session_stats = {}

# Enable native CORS for VS Code Live Server usage
@app.after_request
def apply_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


# ============== WEB UI ==============

@app.route("/")
def index():
    """Serve the main web interface"""
    return render_template("index.html")


@app.route("/login")
def login():
    """Serve the Firebase auth / login page"""
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Redirect to login (client-side Firebase handles actual sign-out)"""
    return redirect("/login")


# ============== PUZZLE API ==============

@app.route("/api/puzzle/generate", methods=["POST"])
def generate_puzzle():
    
    try:
        data = request.get_json() or {}
        difficulty = data.get("difficulty", "medium")
        puzzle_type = data.get("type", "riddle")

        puzzle = puzzle_gen.generate_puzzle(difficulty, puzzle_type)

        if "error" in puzzle:
            # Return 200 so the JS error-check path (puzzle.error) fires
            # instead of the catch block which shows a generic server message.
            return jsonify(puzzle), 200

        return jsonify(puzzle), 201

    except Exception as e:
        return jsonify({"error": str(e), "message": "Internal server error"}), 500


@app.route("/api/puzzle/<puzzle_id>", methods=["GET"])
def get_puzzle(puzzle_id):
    """Get puzzle details (without answer for security)"""
    puzzle = puzzle_gen.get_puzzle(puzzle_id)

    if not puzzle:
        return jsonify({"error": "Puzzle not found"}), 404

    # Strip sensitive fields
    response = {k: v for k, v in puzzle.items() if k not in ("answer", "solution_steps")}
    return jsonify(response), 200


@app.route("/api/puzzle/<puzzle_id>/check", methods=["POST"])
def check_answer(puzzle_id):
    """Validate user's answer against stored puzzle answer"""
    try:
        data = request.get_json() or {}
        user_answer = data.get("answer", "")

        result = puzzle_gen.check_answer(puzzle_id, user_answer)
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/puzzle/<puzzle_id>/hint", methods=["POST"])
def get_hint(puzzle_id):
    """Get a specific hint for a puzzle"""
    try:
        puzzle = puzzle_gen.get_puzzle(puzzle_id)

        if not puzzle:
            return jsonify({"error": "Puzzle not found"}), 404

        data = request.get_json() or {}
        hint_number = data.get("hint_number", 0)

        hint = hint_provider.get_hint(puzzle, hint_number)
        return jsonify({"hint": hint, "hint_number": hint_number}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/puzzle/<puzzle_id>/solution", methods=["GET"])
def get_solution(puzzle_id):
    """Reveal the full solution for a puzzle"""
    puzzle = puzzle_gen.get_puzzle(puzzle_id)

    if not puzzle:
        return jsonify({"error": "Puzzle not found"}), 404

    return jsonify({
        "answer": puzzle.get("answer", "Unknown"),
        "explanation": puzzle.get("explanation", "No explanation available."),
        "solution_steps": puzzle.get("solution_steps", []),
        "hints": puzzle.get("hints", []),
        "validation": puzzle.get("validation", {}),
    }), 200


# ============== CHAT API ==============

@app.route("/api/chat", methods=["POST"])
def chat():
    """Chat with the AI assistant"""
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id", "default")
        user_message = data.get("message", "")
        puzzle_id = data.get("puzzle_id")
        hints_used = data.get("hints_used", 0)
        chat_mode = data.get("chat_mode", "hint_bot")  # hint_bot, free_chat, tutor

        puzzle = None
        if puzzle_id:
            puzzle = puzzle_gen.get_puzzle(puzzle_id)

        response = hint_provider.chat(session_id, user_message, puzzle, hints_used, chat_mode)
        return jsonify({"response": response}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/clear", methods=["POST"])
def clear_chat():
    """Clear conversation history for a session"""
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id", "default")
        hint_provider.clear_conversation(session_id)
        return jsonify({"status": "cleared"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============== SESSION API ==============

@app.route("/api/session/init", methods=["POST"])
def init_session():
    """Initialize or retrieve session stats"""
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id", str(os.urandom(8).hex()))

        if session_id not in session_stats:
            session_stats[session_id] = {
                "session_id": session_id,
                "puzzles_solved": 0,
                "puzzles_attempted": 0,
                "total_hints_used": 0,
                "current_puzzle": None,
                "created_at": datetime.now().isoformat(),
            }

        return jsonify(session_stats[session_id]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/session/<session_id>/stats", methods=["GET"])
def get_stats(session_id):
    """Get session statistics"""
    if session_id not in session_stats:
        return jsonify({"error": "Session not found"}), 404

    return jsonify(session_stats[session_id]), 200


# ============== HEALTH CHECK ==============

@app.route("/api/health", methods=["GET"])
def health():
    """Health check — also surfaces which AI models are currently active."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "puzzle_model": puzzle_gen.active_model_display,
        "chat_model":   hint_provider.active_model_display,
    }), 200


@app.route("/api/model/status", methods=["GET"])
def model_status():
    """
    Returns the active model for both the puzzle generator and the chat
    assistant.  The frontend polls this to display a subtle model indicator.
    """
    return jsonify({
        "puzzle_model": {
            "id":      puzzle_gen.active_model,
            "display": puzzle_gen.active_model_display,
        },
        "chat_model": {
            "id":      hint_provider.active_model,
            "display": hint_provider.active_model_display,
        },
    }), 200


# ============== ANALYTICS API ==============

@app.route("/api/analytics/<user_id>/record", methods=["POST"])
def record_analytics(user_id):
    """Record a puzzle attempt event for analytics tracking."""
    try:
        data = request.get_json() or {}
        snap = analytics_engine.record_attempt(
            user_id,
            puzzle_id    = data.get("puzzle_id", ""),
            difficulty   = data.get("difficulty", "medium"),
            puzzle_type  = data.get("puzzle_type", "riddle"),
            correct      = data.get("correct", False),
            hints_used   = data.get("hints_used", 0),
            time_taken_s = data.get("time_taken_s"),
        )
        return jsonify(snap), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analytics/<user_id>/dashboard", methods=["GET"])
def analytics_dashboard(user_id):
    """Return the full analytics dashboard for a user."""
    try:
        return jsonify(analytics_engine.get_dashboard(user_id)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analytics/<user_id>/events", methods=["GET"])
def analytics_events(user_id):
    """Return recent event log for a user."""
    try:
        limit = int(request.args.get("limit", 50))
        return jsonify(analytics_engine.get_user_events(user_id, limit=limit)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analytics/leaderboard", methods=["GET"])
def analytics_leaderboard():
    """Return the global cognitive score leaderboard."""
    try:
        top_n = int(request.args.get("top", 10))
        return jsonify(analytics_engine.get_leaderboard(top_n=top_n)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============== DIFFICULTY API ==============

@app.route("/api/difficulty/<user_id>/recommend", methods=["GET"])
def recommend_difficulty(user_id):
    """Recommend the next puzzle difficulty for a user."""
    try:
        return jsonify(difficulty_engine.recommend(user_id)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/difficulty/<user_id>/record", methods=["POST"])
def record_difficulty_result(user_id):
    """Record a puzzle result and update the user's Elo rating."""
    try:
        data = request.get_json() or {}
        snap = difficulty_engine.record_result(
            user_id,
            difficulty   = data.get("difficulty", "medium"),
            correct      = data.get("correct", False),
            hints_used   = data.get("hints_used", 0),
            time_taken_s = data.get("time_taken_s"),
        )
        return jsonify(snap), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/difficulty/<user_id>/rating", methods=["GET"])
def get_user_rating(user_id):
    """Return a user's current Elo rating and history."""
    try:
        return jsonify({
            "user_id": user_id,
            "rating":  difficulty_engine.get_rating(user_id),
            "history": difficulty_engine.get_history(user_id, limit=20),
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============== PROGRESS API ==============

@app.route("/api/progress/<user_id>", methods=["GET"])
def get_progress(user_id):
    """Return the full progress profile for a user."""
    try:
        return jsonify(progress_tracker.get_profile(user_id)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/progress/<user_id>/record", methods=["POST"])
def record_progress(user_id):
    """Record a puzzle solve event for progress tracking."""
    try:
        data = request.get_json() or {}
        result = progress_tracker.record_solve(
            user_id,
            puzzle_type  = data.get("puzzle_type", "riddle"),
            difficulty   = data.get("difficulty", "medium"),
            hints_used   = data.get("hints_used", 0),
            correct      = data.get("correct", False),
            time_taken_s = data.get("time_taken_s"),
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/progress/<user_id>/badges", methods=["GET"])
def get_badges(user_id):
    """Return all earned badges for a user."""
    try:
        return jsonify(progress_tracker.get_badges(user_id)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/progress/<user_id>/report", methods=["GET"])
def export_progress_report(user_id):
    """Export a full progress report for a user."""
    try:
        return jsonify(progress_tracker.export_report(user_id)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/progress/<user_id>/goal", methods=["POST"])
def set_weekly_goal(user_id):
    """Set the user's weekly puzzle goal."""
    try:
        data = request.get_json() or {}
        goal = data.get("goal", 15)
        progress_tracker.set_weekly_goal(user_id, goal)
        return jsonify({"status": "updated", "goal": goal}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============== INTERVIEW COACH API ==============

@app.route("/api/interview/<user_id>/start", methods=["POST"])
def start_interview(user_id):
    """Start a new interview coaching session."""
    try:
        data   = request.get_json() or {}
        domain = data.get("domain", "general")
        result = interview_coach.start_session(user_id, domain=domain)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/interview/<user_id>/respond", methods=["POST"])
def interview_respond(user_id):
    """Submit a response to the current interview question."""
    try:
        data     = request.get_json() or {}
        response = data.get("response", "")
        result   = interview_coach.evaluate_response(user_id, response)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/interview/<user_id>/status", methods=["GET"])
def interview_status(user_id):
    """Get the current interview session status."""
    try:
        return jsonify(interview_coach.get_session_status(user_id)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/interview/<user_id>/end", methods=["POST"])
def end_interview(user_id):
    """End the interview session and return a performance summary."""
    try:
        result = interview_coach.end_session(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============== ERROR HANDLERS ==============

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


# ============== RUN ==============

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5002))
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    app.run(host=host, port=port, debug=app.config.get("DEBUG", False))
