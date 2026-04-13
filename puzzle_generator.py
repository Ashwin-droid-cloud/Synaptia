"""
Puzzle Generator Module
3-Tier AI Failover:
  Tier 1 — xAI / Grok API  (cloud, primary)
  Tier 2 — Google Gemini API (cloud, secondary fallback)
  Tier 3 — Local Ollama instance (http://localhost:11434, last resort)

Each tier returns None on any failure, triggering the next tier
automatically — zero user intervention required.
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

# ── Configuration ─────────────────────────────────────────────────────────────

# Tier 1 — xAI / Grok
XAI_API_KEY     = os.getenv("XAI_API_KEY", "")
XAI_MODEL       = os.getenv("XAI_MODEL", "grok-3-mini")
XAI_BASE_URL    = "https://api.x.ai/v1"
XAI_TIMEOUT     = 30   # seconds

# Tier 2 — Google Gemini
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")

# Tier 3 — Local Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3:8b")
OLLAMA_TIMEOUT  = 120  # seconds — local inference can be slow

# ── Puzzle uniqueness helpers ─────────────────────────────────────────────────
# Each list is sampled randomly to produce a unique angle / theme per request.
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


# ═══════════════════════════════════════════════════════════════════════════════
#  TIER 1 — xAI / Grok API
# ═══════════════════════════════════════════════════════════════════════════════

def _xai_generate(prompt: str) -> Optional[str]:
    """
    Call the xAI (Grok) API via OpenAI-compatible chat completions.
    Returns the response text, or None on any failure.
    """
    if not XAI_API_KEY:
        logger.info("[PuzzleGen] No XAI_API_KEY set — xAI tier disabled.")
        return None
    url = f"{XAI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": XAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": 1.0,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=XAI_TIMEOUT)
        if resp.status_code == 403:
            logger.warning("[PuzzleGen] xAI 403 — no credits/quota: %s — falling back to Gemini.", resp.text[:200])
            return None
        if resp.status_code == 429:
            logger.warning("[PuzzleGen] xAI rate-limit hit — falling back to Gemini.")
            return None
        resp.raise_for_status()
        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        if text:
            logger.info("[PuzzleGen] xAI (Grok) responded successfully.")
        return text or None
    except requests.exceptions.Timeout:
        logger.warning("[PuzzleGen] xAI request timed out — falling back to Gemini.")
        return None
    except requests.exceptions.ConnectionError:
        logger.warning("[PuzzleGen] Cannot reach xAI API — falling back to Gemini.")
        return None
    except Exception as exc:
        logger.warning("[PuzzleGen] xAI error: %s — falling back to Gemini.", exc)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  TIER 2 — Google Gemini API
# ═══════════════════════════════════════════════════════════════════════════════

_gemini_model = None
_gemini_available = False

def _init_gemini():
    """Lazy-initialise the Gemini client. Called once on first use."""
    global _gemini_model, _gemini_available
    if _gemini_model is not None:
        return _gemini_available
    if not GEMINI_API_KEY:
        logger.info("[PuzzleGen] No GEMINI_API_KEY set — Gemini tier disabled.")
        _gemini_available = False
        return False
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel("gemini-2.0-flash")
        _gemini_available = True
        logger.info("[PuzzleGen] Gemini API initialised successfully (gemini-2.0-flash).")
        return True
    except Exception as exc:
        logger.warning("[PuzzleGen] Gemini init failed: %s — will use Ollama.", exc)
        _gemini_available = False
        return False


def _gemini_generate(prompt: str) -> Optional[str]:
    """
    Call Google Gemini to generate content.
    Returns the text response, or None on any failure (quota, network, etc.).
    """
    if not _init_gemini():
        return None
    try:
        response = _gemini_model.generate_content(prompt)
        text = response.text.strip() if response.text else None
        if text:
            logger.info("[PuzzleGen] Gemini responded successfully.")
        return text
    except Exception as exc:
        err_str = str(exc).lower()
        if "quota" in err_str or "rate" in err_str or "429" in err_str or "resource" in err_str:
            logger.warning("[PuzzleGen] Gemini quota/rate-limit hit: %s — falling back to Ollama.", exc)
        else:
            logger.warning("[PuzzleGen] Gemini error: %s — falling back to Ollama.", exc)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  TIER 2 — Local Ollama (http://localhost:11434)
# ═══════════════════════════════════════════════════════════════════════════════

def _ollama_chat(messages: list, temperature: float = 1.0) -> Optional[str]:
    """
    Send a chat request to the local Ollama instance.

    Args:
        messages:    List of {"role": ..., "content": ...} dicts.
        temperature: Sampling temperature.

    Returns:
        The assistant's response string, or None on failure.
    """
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model":   OLLAMA_MODEL,
        "messages": messages,
        "stream":  False,
        "options": {
            "temperature": temperature,
        },
    }
    try:
        resp = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "").strip() or None
    except requests.exceptions.ConnectionError:
        logger.error(
            "[PuzzleGen] Cannot reach Ollama at %s — is it running?", OLLAMA_BASE_URL
        )
        return None
    except requests.exceptions.Timeout:
        logger.error("[PuzzleGen] Ollama request timed out after %ds.", OLLAMA_TIMEOUT)
        return None
    except Exception as exc:
        logger.error("[PuzzleGen] Ollama error: %s", exc)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  PuzzleGenerator
# ═══════════════════════════════════════════════════════════════════════════════

class PuzzleGenerator:
    """
    Generates logic puzzles using a 2-tier AI failover:
      Tier 1: Google Gemini API (cloud)
      Tier 2: Local Ollama (http://localhost:11434)
    """

    def __init__(self, *args, **kwargs):
        # Accept (and ignore) any legacy api_key argument for compatibility.
        self.puzzles: dict = {}
        # Track recent prompt angles to avoid repetition within a session
        self._recent_tags: list = []
        # Track which model was last used
        self._last_model_used: str = "Initializing..."
        self._last_model_id: str = ""

    # ── Active model (for health / status endpoints) ──────────────────────────

    @property
    def active_model(self) -> str:
        return self._last_model_id or OLLAMA_MODEL

    @property
    def active_model_display(self) -> str:
        return self._last_model_used or "Llama 3 8B (Local)"

    # ── Puzzle generation ─────────────────────────────────────────────────────

    def generate_puzzle(self, difficulty="medium", puzzle_type="riddle"):
        try:
            prompt_text = self._build_prompt_text(difficulty, puzzle_type)
            messages = self._build_messages(difficulty, puzzle_type)

            # ── TIER 1: Try xAI / Grok first ─────────────────────────────────
            puzzle_content = _xai_generate(prompt_text)
            if puzzle_content:
                model_display = f"Grok ({XAI_MODEL}) (Cloud)"
                model_id = XAI_MODEL
            else:
                # ── TIER 2: Try Gemini ────────────────────────────────────────
                logger.info("[PuzzleGen] Trying Gemini (Tier 2)...")
                puzzle_content = _gemini_generate(prompt_text)
                if puzzle_content:
                    model_display = "Gemini 2.0 Flash (Cloud)"
                    model_id = "gemini-2.0-flash"
                else:
                    # ── TIER 3: Fall back to local Ollama ─────────────────────
                    logger.info("[PuzzleGen] Trying Ollama (Tier 3)...")
                    puzzle_content = _ollama_chat(messages, temperature=1.0)
                    model_display = "Llama 3 8B (Local)"
                    model_id = OLLAMA_MODEL

            if puzzle_content is None:
                return {
                    "error": (
                        "All AI models are currently unavailable. "
                        "xAI (Grok) has no credits, Gemini may be exhausted, "
                        "and Ollama is not reachable. "
                        f"Please ensure Ollama is running at {OLLAMA_BASE_URL} "
                        f"with model '{OLLAMA_MODEL}' loaded."
                    )
                }

            self._last_model_used = model_display
            self._last_model_id = model_id

            puzzle = self._parse_puzzle(puzzle_content, difficulty, puzzle_type)
            puzzle_id = str(uuid.uuid4())[:8]
            puzzle["id"]         = puzzle_id
            puzzle["created_at"] = datetime.now().isoformat()
            puzzle["model_used"] = model_display
            self.puzzles[puzzle_id] = puzzle
            return puzzle

        except Exception as e:
            logger.error("[PuzzleGen] Unhandled exception: %s", e)
            return {"error": str(e), "message": "Failed to generate puzzle"}

    # ── Prompt / message building ─────────────────────────────────────────────

    def _build_prompt_text(self, difficulty, puzzle_type) -> str:
        """Build a single prompt string (used for Gemini)."""
        messages = self._build_messages(difficulty, puzzle_type)
        # Combine system + user messages into a single prompt for Gemini
        parts = []
        for m in messages:
            parts.append(m["content"])
        return "\n\n".join(parts)

    def _build_messages(self, difficulty, puzzle_type) -> list:
        """Build the Ollama chat messages list for puzzle generation."""
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

        # ── Uniqueness enforcer ───────────────────────────────────────────────
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
        """
        Extract the first complete JSON object from raw text using brace-depth
        counting. Handles chain-of-thought tokens that appear before the JSON.
        """
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
        """
        Replace literal newline/carriage-return/tab characters that appear
        inside JSON string values with their escaped equivalents.
        """
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
        """
        Robustly parse AI output into a structured puzzle dictionary.

        Three-layer extraction strategy:
          Layer 1  Extract the JSON object boundaries (brace-depth scan).
          Layer 2  Sanitize literal whitespace inside string values.
          Layer 3  Markdown-fence strip as a last-resort fallback.
        """
        import re
        try:
            raw = content.strip()

            # Layer 1 — extract JSON object; handles chain-of-thought preamble
            extracted = self._extract_json_object(raw)

            # Layer 2 — sanitize literal newlines inside string values
            sanitized = self._sanitize_string_values(extracted)

            try:
                puzzle_data = json.loads(sanitized)
            except json.JSONDecodeError:
                # Layer 3 — try markdown-fence strip, then re-extract + re-sanitize
                fence_match = re.search(r"```(?:json)?(.*?)```", raw, re.DOTALL | re.IGNORECASE)
                if fence_match:
                    candidate = fence_match.group(1).strip()
                else:
                    candidate = self._extract_json_object(self._sanitize_string_values(raw))

                puzzle_data = json.loads(candidate)

            # Normalise metadata
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

        # Graceful fallback — reached only if all three layers fail
        return {
            "question": "The puzzle could not be decoded at this time. Please regenerate.",
            "answer": "N/A",
            "explanation": "The AI response could not be parsed. This occasionally occurs with complex types. Try regenerating.",
            "difficulty": difficulty,
            "type": puzzle_type,
            "hints": [
                "Please regenerate this puzzle using the button above.",
                "Complex types such as Logic occasionally produce parse errors.",
                "Switching to Riddle or Math yields the highest parse reliability.",
            ],
            "solution_steps": ["Regenerate the puzzle to receive a valid challenge."],
            "solved": False,
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
            return {"error": "Puzzle not found"}

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
            "answer": puzzle["answer"] if correct else None,
        }
