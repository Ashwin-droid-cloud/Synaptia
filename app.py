"""
Synaptia — Flask Application
Main server with API routes for exercise generation, hints, chat, and answer checking.
Powered by a 3-tier AI failover system (OpenRouter -> Gemini -> Ollama).
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from config import config
from puzzle_generator import PuzzleGenerator
from hint_provider import HintProvider
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
puzzle_gen = PuzzleGenerator()
hint_provider = HintProvider()

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


# ============== PUZZLE API ==============

@app.route("/api/puzzle/generate", methods=["POST"])
def generate_puzzle():
    """Generate a new puzzle via local Ollama model"""
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
