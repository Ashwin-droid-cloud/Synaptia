"""
Puzzle Generator Module — Synaptia
Powered entirely by the Groq API (groq.com) — llama-3.3-70b-versatile.
Uses the OpenAI-compatible endpoint at https://api.groq.com/openai/v1.
"""

import re as _re
import json
import uuid
import time
import os
import random
import logging
import requests
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Groq API Configuration ──────────────────────────────────────────────────

GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "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")
GROQ_MODEL    = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_TIMEOUT  = 60

# ── Puzzle uniqueness helpers ────────────────────────────────────────────────

_RIDDLE_ANGLES = [
    "nature and animals", "everyday household objects", "weather phenomena",
    "technology and computers", "the human body", "food and cooking",
    "time and clocks", "music and sound", "light and shadows",
    "books and libraries", "oceans and rivers", "astronomy and space",
    "travel and transportation", "money and economics", "language and words",
    "mountains and geography", "art and painting", "sports and games",
    "history and ancient civilisations", "mathematics and patterns",
    "emotions and psychology", "plants and forests", "sports equipment",
    "clothing and fashion", "medicine and health",
]
_MATH_ANGLES = [
    "number theory", "geometry and shapes", "probability and statistics",
    "sequences and series", "combinatorics", "algebra and equations",
    "rates and ratios", "percentages and fractions", "prime numbers",
    "logic grids and constraints", "modular arithmetic", "Fibonacci patterns",
    "graph theory concepts", "clock arithmetic", "coin and weight problems",
]
_LOGIC_ANGLES = [
    "truth-teller/liar scenarios", "island inhabitants", "grid deduction",
    "scheduling conflicts", "river crossing", "coin weighing",
    "coloured hats", "job assignments", "seating arrangements",
    "family relationships", "prisoners dilemma variants", "cryptic clues",
    "lateral thinking scenarios", "elimination grids", "conditional statements",
]
_WORDPLAY_ANGLES = [
    "homophones", "anagrams", "palindromes", "compound words",
    "idioms taken literally", "portmanteau words", "double meanings",
    "spoonerisms", "backronyms", "etymological surprises",
    "words hidden inside other words", "foreign loan words",
    "oxymorons", "contronyms", "phobias and their names",
]
_TRIVIA_ANGLES = [
    "ancient history", "famous inventors", "world records",
    "animal behaviour", "space exploration", "geography extremes",
    "language origins", "food history", "medical breakthroughs",
    "classic literature", "scientific constants", "cultural traditions",
    "historical firsts", "bizarre laws around the world", "architectural wonders",
]
_ANGLE_MAP = {
    "riddle":   _RIDDLE_ANGLES,
    "math":     _MATH_ANGLES,
    "logic":    _LOGIC_ANGLES,
    "wordplay": _WORDPLAY_ANGLES,
    "trivia":   _TRIVIA_ANGLES,
}


# ── Groq API call ────────────────────────────────────────────────────────────

def _groq_generate(messages: list, max_tokens: int = 1024, temperature: float = 1.0) -> Optional[str]:
    """
    Call the Groq API via its OpenAI-compatible chat/completions endpoint.
    Returns the text response, or None on any failure.
    """
    url = f"{GROQ_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       GROQ_MODEL,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": temperature,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=GROQ_TIMEOUT)
        if resp.status_code == 401:
            logger.error("[PuzzleGen] Groq API: invalid API key (401). Raw: %s", resp.text[:200])
            return None
        if resp.status_code == 429:
            logger.warning("[PuzzleGen] Groq API: rate limit hit (429). Retrying in 5s…")
            time.sleep(5)
            resp = requests.post(url, headers=headers, json=payload, timeout=GROQ_TIMEOUT)
            resp.raise_for_status()
        resp.raise_for_status()
        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        if text:
            logger.info("[PuzzleGen] Groq (%s) responded successfully.", GROQ_MODEL)
        return text or None
    except requests.exceptions.Timeout:
        logger.error("[PuzzleGen] Groq API request timed out.")
        return None
    except requests.exceptions.ConnectionError as exc:
        logger.error("[PuzzleGen] Cannot reach Groq API: %s", exc)
        return None
    except Exception as exc:
        logger.error("[PuzzleGen] Groq API error: %s", exc)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  PuzzleGenerator
# ═══════════════════════════════════════════════════════════════════════════════

class PuzzleGenerator:
    """
    Generates cognitive exercises using the Groq API (groq.com).
    Model: llama-3.3-70b-versatile (ultra-fast inference, free tier).
    """

    def __init__(self, *args, **kwargs):
        self.puzzles: dict = {}
        self._recent_tags: list = []
        self._last_model_used: str = f"Groq / {GROQ_MODEL}"
        self._last_model_id: str = GROQ_MODEL

    # ── Active model (for health / status endpoints) ──────────────────────────

    @property
    def active_model(self) -> str:
        return self._last_model_id or GROQ_MODEL

    @property
    def active_model_display(self) -> str:
        return self._last_model_used or f"Groq / {GROQ_MODEL}"

    # ── Puzzle generation ─────────────────────────────────────────────────────

    def generate_puzzle(self, difficulty="medium", puzzle_type="riddle"):
        try:
            messages = self._build_messages(difficulty, puzzle_type)
            puzzle_content = _groq_generate(messages, max_tokens=1024, temperature=1.0)

            if puzzle_content is None:
                return {
                    "error": (
                        "Groq API is currently unavailable. "
                        "Please verify your GROQ_API_KEY and try again."
                    )
                }

            self._last_model_used = f"Groq / {GROQ_MODEL}"
            self._last_model_id = GROQ_MODEL

            puzzle = self._parse_puzzle(puzzle_content, difficulty, puzzle_type)
            puzzle_id = str(uuid.uuid4())[:8]
            puzzle["id"]         = puzzle_id
            puzzle["created_at"] = datetime.now().isoformat()
            puzzle["model_used"] = self._last_model_used
            self.puzzles[puzzle_id] = puzzle
            return puzzle

        except Exception as e:
            logger.error("[PuzzleGen] Unhandled exception: %s", e)
            return {"error": str(e), "message": "Failed to generate puzzle"}

    # ── Prompt / message building ─────────────────────────────────────────────

    def _build_messages(self, difficulty, puzzle_type) -> list:
        """Build the chat messages list for puzzle generation."""
        system_content = (
            "You are a world-class puzzle master with an encyclopaedic knowledge "
            "of riddles, logic, mathematics, wordplay, and trivia. "
            "You ALWAYS create unique, original puzzles — never repeat a puzzle you have given before. "
            "Respond with ONLY valid JSON. No markdown, no code fences, no extra text whatsoever."
        )

        difficulty_desc = {
            "easy":   "suitable for beginners, straightforward logic with clear reasoning",
            "medium": "moderate difficulty requiring creative thinking and analysis",
            "hard":   "challenging puzzle requiring deep logical reasoning and multi-step problem-solving",
        }
        puzzle_type_desc = {
            "riddle":   "a clever riddle or wordplay puzzle with a surprising, satisfying answer",
            "math":     "a mathematical logic puzzle requiring calculation and deduction",
            "logic":    "a deductive logic puzzle requiring systematic elimination",
            "wordplay": "a lateral thinking or wordplay brain teaser",
            "trivia":   "an interesting trivia question with a fascinating explanation",
        }
        base_diff   = difficulty_desc.get(difficulty, "moderate difficulty")
        puzzle_desc = puzzle_type_desc.get(puzzle_type, "an engaging riddle")

        angle_pool = _ANGLE_MAP.get(puzzle_type, _RIDDLE_ANGLES)
        fresh = [a for a in angle_pool if a not in self._recent_tags]
        if not fresh:
            fresh = angle_pool
            self._recent_tags = []

        angle = random.choice(fresh)
        nonce = uuid.uuid4().hex[:8]

        self._recent_tags.append(angle)
        if len(self._recent_tags) > len(angle_pool) // 2:
            self._recent_tags.pop(0)

        user_content = f"""Create {puzzle_desc} ({base_diff}).

UNIQUENESS DIRECTIVE — CRITICAL:
- Theme / domain: "{angle}"
- Session nonce: {nonce}  ← use this as creative inspiration seed
- The puzzle MUST be original and MUST NOT be a common or well-known puzzle.
- Do NOT repeat standard classics (e.g. "I speak without a mouth", "man in an elevator", "Tuesday").

REQUIREMENTS:
- Puzzle must be interesting, engaging, and NOT trivial
- Answer must be clear, correct, and verifiable
- Provide exactly 3 progressive hints (each as a plain string, no newlines inside strings)
- Provide 2-3 solution steps explaining the reasoning (each as a plain string)
- ALL string values must be on a single line — do NOT use literal newline characters inside any string value

Return ONLY valid JSON with this exact structure:
{{
    "question": "The complete puzzle question on a single line",
    "answer": "The single correct answer (1-3 words ideally)",
    "explanation": "Clear 1-2 sentence explanation on a single line",
    "hints": [
        "Hint 1: subtle directional clue on one line",
        "Hint 2: narrows possibilities significantly on one line",
        "Hint 3: strong hint that almost reveals the answer on one line"
    ],
    "solution_steps": [
        "Step 1: First part of the logical reasoning on one line",
        "Step 2: How to arrive at the answer on one line",
        "Step 3: Why this answer is definitive on one line"
    ],
    "category": "{puzzle_type}",
    "difficulty": "{difficulty}"
}}"""

        return [
            {"role": "system", "content": system_content},
            {"role": "user",   "content": user_content},
        ]

    # ── Parsing Infrastructure ─────────────────────────────────────────────────

    def _extract_json_object(self, text):
        start = text.find('{')
        if start == -1:
            return text

        depth = 0
        in_string = False
        escape_next = False

        for i in range(start, len(text)):
            c = text[i]
            if escape_next:
                escape_next = False
                continue
            if c == '\\' and in_string:
                escape_next = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]

        end = text.rfind('}')
        if end > start:
            return text[start:end + 1]
        return text

    def _sanitize_string_values(self, content):
        result = []
        in_string = False
        escape_next = False

        for c in content:
            if escape_next:
                result.append(c)
                escape_next = False
            elif c == '\\' and in_string:
                result.append(c)
                escape_next = True
            elif c == '"':
                in_string = not in_string
                result.append(c)
            elif c == '\n' and in_string:
                result.append('\\n')
            elif c == '\r' and in_string:
                result.append('\\r')
            elif c == '\t' and in_string:
                result.append('\\t')
            else:
                result.append(c)

        return ''.join(result)

    def _parse_puzzle(self, content, difficulty, puzzle_type):
        import re
        try:
            raw = content.strip()
            extracted = self._extract_json_object(raw)
            sanitized = self._sanitize_string_values(extracted)

            try:
                puzzle_data = json.loads(sanitized)
            except json.JSONDecodeError:
                fence_match = re.search(r"```(?:json)?(.*?)```", raw, re.DOTALL | re.IGNORECASE)
                if fence_match:
                    candidate = fence_match.group(1).strip()
                else:
                    candidate = self._extract_json_object(self._sanitize_string_values(raw))
                puzzle_data = json.loads(candidate)

            puzzle_data["difficulty"] = difficulty
            puzzle_data["type"]       = puzzle_type
            puzzle_data["solved"]     = False

            if "solution_steps" not in puzzle_data:
                puzzle_data["solution_steps"] = [puzzle_data.get("explanation", "No explanation available.")]
            elif isinstance(puzzle_data["solution_steps"], str):
                puzzle_data["solution_steps"] = [puzzle_data["solution_steps"]]

            if "hints" in puzzle_data and isinstance(puzzle_data["hints"], str):
                puzzle_data["hints"] = [puzzle_data["hints"]]

            return puzzle_data

        except Exception as e:
            logger.error("[PuzzleGen] Parse failure — %s | Raw excerpt: %s", e, content[:300])

        return {
            "question":       "The exercise could not be decoded at this time. Please regenerate.",
            "answer":         "N/A",
            "explanation":    "The AI response could not be parsed. Please try regenerating.",
            "difficulty":     difficulty,
            "type":           puzzle_type,
            "hints":          ["Please regenerate this exercise."],
            "solution_steps": ["Regenerate the exercise to receive a valid challenge."],
            "solved":         False,
        }

    # ── Retrieval & Validation ─────────────────────────────────────────────────

    def get_puzzle(self, puzzle_id):
        return self.puzzles.get(puzzle_id)

    def list_puzzles(self):
        safe_list = []
        for p in self.puzzles.values():
            safe = {k: v for k, v in p.items() if k not in ("answer", "solution_steps")}
            safe_list.append(safe)
        return safe_list

    def check_answer(self, puzzle_id, user_answer):
        """Check if the user's answer is correct using normalised fuzzy matching."""
        puzzle = self.get_puzzle(puzzle_id)
        if not puzzle:
            return {"error": "Exercise not found"}

        import re
        from difflib import SequenceMatcher

        user_norm    = re.sub(r'[^a-z0-9\s]', '', user_answer.lower().strip())
        correct_norm = re.sub(r'[^a-z0-9\s]', '', puzzle["answer"].lower().strip())

        correct = False

        if user_norm == correct_norm:
            correct = True
        else:
            stopwords = {"a", "an", "the", "it", "is", "its", "of", "and"}
            user_tokens    = set(user_norm.split()) - stopwords
            correct_tokens = set(correct_norm.split()) - stopwords

            if user_tokens == correct_tokens and len(correct_tokens) > 0:
                correct = True
            elif correct_tokens and correct_tokens.issubset(user_tokens):
                correct = True
            elif correct_tokens and user_tokens:
                meaningful = {w for w in correct_tokens if len(w) > 3}
                if meaningful and meaningful.intersection(user_tokens):
                    correct = True

            if not correct and len(correct_norm) > 3:
                ratio = SequenceMatcher(None, user_norm, correct_norm).ratio()
                if ratio > 0.8:
                    correct = True

        if correct:
            puzzle["solved"] = True

        return {
            "correct": correct,
            "answer":  puzzle["answer"] if correct else None,
        }
