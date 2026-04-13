"""
Hint Provider Module
Multi-mode AI chatbot with 3-tier failover:
  Tier 1 — xAI / Grok API  (cloud, primary)
  Tier 2 — Google Gemini API (cloud, secondary fallback)
  Tier 3 — Local Ollama instance (last resort)
"""

import requests
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ── Tier 1: xAI / Grok ───────────────────────────────────────────────────────

XAI_API_KEY  = os.getenv("XAI_API_KEY", "")
XAI_MODEL    = os.getenv("XAI_MODEL", "grok-3-mini")
XAI_BASE_URL = "https://api.x.ai/v1"
XAI_TIMEOUT  = 30

# ── Tier 2: Google Gemini ─────────────────────────────────────────────────────

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
_gemini_chat_model = None
_gemini_chat_available = False

# ── Tier 3: Ollama Configuration ──────────────────────────────────────────────

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3:8b")
OLLAMA_TIMEOUT  = 120  # seconds


# ── Tier-1 helper: xAI / Grok ────────────────────────────────────────────────

def _xai_chat(messages: list, temperature: float = 0.75, max_tokens: int = 600) -> Optional[str]:
    """
    Send a chat request to xAI (Grok) via the OpenAI-compatible endpoint.
    Returns the assistant's response string, or None on failure.
    """
    if not XAI_API_KEY:
        return None
    url = f"{XAI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type":  "application/json",
    }

    # Grok supports system/user/assistant roles natively via xAI's API
    payload = {
        "model":       XAI_MODEL,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": temperature,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=XAI_TIMEOUT)
        if resp.status_code in (403, 429):
            logger.warning("[HintProvider] xAI %s — falling back to Gemini.", resp.status_code)
            return None
        resp.raise_for_status()
        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        if text:
            logger.info("[HintProvider] xAI (Grok) responded successfully.")
        return text or None
    except requests.exceptions.Timeout:
        logger.warning("[HintProvider] xAI request timed out — falling back to Gemini.")
        return None
    except requests.exceptions.ConnectionError:
        logger.warning("[HintProvider] Cannot reach xAI API — falling back to Gemini.")
        return None
    except Exception as exc:
        logger.warning("[HintProvider] xAI error: %s — falling back to Gemini.", exc)
        return None


# ── Tier-2 helper: Google Gemini ─────────────────────────────────────────────

def _init_gemini_chat():
    """Lazy-init Gemini for the chat assistant (shared module-level state)."""
    global _gemini_chat_model, _gemini_chat_available
    if _gemini_chat_model is not None:
        return _gemini_chat_available
    if not GEMINI_API_KEY:
        _gemini_chat_available = False
        return False
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_chat_model = genai.GenerativeModel("gemini-2.0-flash")
        _gemini_chat_available = True
        logger.info("[HintProvider] Gemini chat model initialised.")
        return True
    except Exception as exc:
        logger.warning("[HintProvider] Gemini init failed: %s", exc)
        _gemini_chat_available = False
        return False


def _gemini_chat(messages: list, max_tokens: int = 600) -> Optional[str]:
    """
    Send a chat request to Google Gemini.
    Returns the assistant's response string, or None on failure.
    """
    if not _init_gemini_chat():
        return None
    # Collapse all messages into a single prompt for Gemini
    parts = []
    for m in messages:
        role_label = ""
        if m["role"] == "system":
            role_label = "[System] "
        elif m["role"] == "assistant":
            role_label = "[Assistant] "
        parts.append(f"{role_label}{m['content']}")
    prompt = "\n\n".join(parts)
    try:
        response = _gemini_chat_model.generate_content(prompt)
        text = response.text.strip() if response.text else None
        if text:
            logger.info("[HintProvider] Gemini responded successfully.")
        return text
    except Exception as exc:
        err = str(exc).lower()
        if "quota" in err or "429" in err or "rate" in err:
            logger.warning("[HintProvider] Gemini quota hit — falling back to Ollama.")
        else:
            logger.warning("[HintProvider] Gemini error: %s — falling back to Ollama.", exc)
        return None


# ── Tier-3 helper: Local Ollama ───────────────────────────────────────────────

def _ollama_chat(messages: list, temperature: float = 0.75, max_tokens: int = 600) -> Optional[str]:
    """
    Send a chat request to the local Ollama instance.

    Args:
        messages:    List of {"role": ..., "content": ...} dicts.
        temperature: Sampling temperature.
        max_tokens:  Maximum tokens to generate (via num_predict).

    Returns:
        The assistant's response string, or None on failure.
    """
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model":    OLLAMA_MODEL,
        "messages": messages,
        "stream":   False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    try:
        resp = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "").strip() or None
    except requests.exceptions.ConnectionError:
        logger.error(
            "[HintProvider] Cannot reach Ollama at %s — is it running?", OLLAMA_BASE_URL
        )
        return None
    except requests.exceptions.Timeout:
        logger.error("[HintProvider] Ollama request timed out after %ds.", OLLAMA_TIMEOUT)
        return None
    except Exception as exc:
        logger.error("[HintProvider] Ollama error: %s", exc)
        return None


# ── HintProvider ──────────────────────────────────────────────────────────────

class HintProvider:
    """Provides hints and multi-mode AI chatbot functionality for puzzles."""

    _FALLBACK_RESPONSES = [
        (
            "I'm temporarily unable to reach any AI model. "
            "Please check your xAI credits, Gemini quota, or ensure Ollama is running "
            f"at {OLLAMA_BASE_URL} with model '{OLLAMA_MODEL}' loaded, then try again."
        ),
        (
            "All AI models are currently unavailable. "
            "Please verify your xAI API credits are loaded or Ollama is running with llama3:8b."
        ),
        (
            "I couldn't get a response from any AI provider. "
            "Please verify your xAI API key has credits, or retry when Ollama is running."
        ),
    ]
    _fallback_index = 0  # class-level so each call gives a varied message

    def __init__(self, *args, **kwargs):
        # Accept (and ignore) any legacy api_key argument for compatibility.
        self.conversations: dict = {}  # session_id -> message list
        self._active_model_id: str = ""
        self._active_model_display: str = "Initializing..."

    # ── Public: active model ─────────────────────────────────────────────────

    @property
    def active_model(self) -> str:
        return self._active_model_id or OLLAMA_MODEL

    @property
    def active_model_display(self) -> str:
        return self._active_model_display or "Llama 3 8B (Local)"

    # ── Public: hints ────────────────────────────────────────────────────────

    def get_hint(self, puzzle: dict, hint_number: int = 0) -> str:
        """
        Return a hint for *puzzle*.

        Prefers pre-generated hints embedded in the puzzle dict; falls back
        to a dynamically generated hint if unavailable.
        """
        if puzzle.get("hints") and hint_number < len(puzzle["hints"]):
            return puzzle["hints"][hint_number]
        return self._generate_hint(puzzle, hint_number)

    def _generate_hint(self, puzzle: dict, hint_number: int) -> str:
        """Generate a dynamic hint via the best available AI tier."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a puzzle hint assistant. "
                    "Generate a single concise hint. Return ONLY the hint text, nothing else."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Puzzle: {puzzle.get('question', '')}\n"
                    f"Answer: {puzzle.get('answer', '')}\n\n"
                    f"Generate hint #{hint_number + 1}. "
                    "Progressive difficulty: "
                    "Clue I — subtle, directional nudge; "
                    "Clue II — stronger, narrows possibilities; "
                    "Clue III — almost reveals the answer.\n"
                    "Return ONLY the hint text."
                ),
            },
        ]
        result = (
            _xai_chat(messages, temperature=0.7, max_tokens=200)
            or _gemini_chat(messages, max_tokens=200)
            or _ollama_chat(messages, temperature=0.7, max_tokens=200)
        )
        return result or "Unable to generate a hint at this time. Please try again shortly."

    # ── Public: chat ─────────────────────────────────────────────────────────

    def chat(
        self,
        session_id: str,
        user_message: str,
        puzzle: dict = None,
        hints_used: int = 0,
        chat_mode: str = "hint_bot",
    ) -> str:
        """
        Send a message and receive an AI response.

        Args:
            session_id:   Unique identifier for this conversation.
            user_message: The user's input text.
            puzzle:       Current puzzle dict (optional context).
            hints_used:   Number of hints consumed (anti-cheat gate).
            chat_mode:    'hint_bot' | 'free_chat' | 'tutor' | 'creative'

        Returns:
            AI response string (guaranteed non-empty).
        """
        if session_id not in self.conversations:
            self.conversations[session_id] = []

        system_content = self._build_system_prompt(puzzle, hints_used, chat_mode)

        # Append user turn to history
        self.conversations[session_id].append(
            {"role": "user", "content": user_message}
        )

        # Build messages list (system + last 12 turns for context)
        messages = [{"role": "system", "content": system_content}]
        messages += [
            {"role": m["role"] if m["role"] in ("user", "assistant") else "user",
             "content": m["content"]}
            for m in self.conversations[session_id][-12:]
        ]

        # 3-tier failover: xAI → Gemini → Ollama
        response_text = (
            _xai_chat(messages, temperature=0.75, max_tokens=600)
            or _gemini_chat(messages, max_tokens=600)
            or _ollama_chat(messages, temperature=0.75, max_tokens=600)
        )

        if response_text:
            self.conversations[session_id].append(
                {"role": "assistant", "content": response_text}
            )
        else:
            response_text = self._next_fallback()
            logger.warning("[HintProvider] All tiers unavailable; sending fallback to user.")

        return response_text

    def clear_conversation(self, session_id: str) -> bool:
        """Delete conversation history for *session_id*."""
        if session_id in self.conversations:
            del self.conversations[session_id]
            return True
        return False

    # ── Fallback message rotation ─────────────────────────────────────────────

    def _next_fallback(self) -> str:
        """Return the next fallback message in sequence."""
        msg = HintProvider._FALLBACK_RESPONSES[HintProvider._fallback_index]
        HintProvider._fallback_index = (
            HintProvider._fallback_index + 1
        ) % len(HintProvider._FALLBACK_RESPONSES)
        return msg

    # ── System prompts ───────────────────────────────────────────────────────

    def _build_system_prompt(
        self, puzzle: dict, hints_used: int, chat_mode: str
    ) -> str:
        """Construct a role-specific system instruction for the given mode."""

        mode_prompts = {
            "hint_bot": (
                "You are PuzzleAI's Hint Assistant — a precise, encouraging guide whose "
                "sole objective is to help users reason their way to the correct answer "
                "without handing it to them prematurely.\n"
                "PRINCIPLES:\n"
                "1. Provide directional guidance, not direct answers.\n"
                "2. Ask Socratic questions that steer thinking.\n"
                "3. Keep responses concise — two to four sentences.\n"
                "4. Celebrate reasoning progress, not just correct answers.\n"
                "5. Maintain a calm, professional, yet warm tone."
            ),
            "free_chat": (
                "You are PuzzleAI's Open Dialogue assistant — a knowledgeable, engaging "
                "conversationalist capable of discussing any topic with depth and clarity.\n"
                "PRINCIPLES:\n"
                "1. Respond thoughtfully and with intellectual substance.\n"
                "2. Keep answers focused — three to five sentences unless more is warranted.\n"
                "3. Share interesting perspectives and well-reasoned opinions.\n"
                "4. Maintain a professional yet approachable tone.\n"
                "5. Freely discuss puzzles, cognitive science, technology, or anything else."
            ),
            "tutor": (
                "You are Professor Puzzle — PuzzleAI's Guided Tutor. Your mission is to "
                "build the user's reasoning capabilities through structured, patient instruction.\n"
                "PRINCIPLES:\n"
                "1. Break complex logic into numbered, digestible steps.\n"
                "2. Ask questions that prompt independent discovery before giving answers.\n"
                "3. Identify and gently correct logical misconceptions.\n"
                "4. Reinforce correct reasoning with brief, specific praise.\n"
                "5. Use analogies and concrete examples where abstract reasoning is involved."
            ),
            "creative": (
                "You are the Creative Analyst — PuzzleAI's lateral thinking specialist. "
                "You help users explore unconventional solution paths through imaginative reasoning.\n"
                "PRINCIPLES:\n"
                "1. Challenge obvious interpretations — look for unexpected angles.\n"
                "2. Draw on metaphor, wordplay, and cross-domain analogies.\n"
                "3. Encourage speculative thinking without sacrificing rigour.\n"
                "4. Keep the intellectual energy curious and exploratory.\n"
                "5. Validate unusual ideas — creative leaps are assets, not distractions."
            ),
        }

        system = mode_prompts.get(chat_mode, mode_prompts["hint_bot"])

        # Append puzzle context for hint_bot mode
        if puzzle and chat_mode == "hint_bot":
            system += (
                f"\n\nACTIVE PUZZLE CONTEXT:\n"
                f"Question: {puzzle.get('question', '')}\n"
                f"Answer: {puzzle.get('answer', '')}\n"
                f"Difficulty: {puzzle.get('difficulty', 'medium')}\n"
                f"Type: {puzzle.get('type', 'riddle')}"
            )
            if hints_used < 2:
                system += (
                    "\n\nIMPORTANT CONSTRAINT: The user has used fewer than two hints. "
                    "Do NOT reveal the answer even if explicitly requested. "
                    "Direct them to use the hint buttons first."
                )
            else:
                system += (
                    "\n\nThe user has consumed two or more hints. If they explicitly and "
                    "persistently request the full answer, you may reveal it — but first "
                    "encourage one final independent attempt."
                )

        return system
