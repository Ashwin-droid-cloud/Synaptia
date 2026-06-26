"""
Interview Coach Module — Synaptia
AI-powered mock interview assistant powered by the Groq API (groq.com).
Conducts domain-specific cognitive and technical interview simulations,
provides structured feedback, and tracks session performance.

Status: Scaffolded — ready for route integration in app.py.
"""

import os
import logging
import time
import requests
from dotenv import load_dotenv

load_dotenv()
from typing import Optional

logger = logging.getLogger(__name__)

# ── Groq API Configuration ────────────────────────────────────────────────────

GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL    = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_TIMEOUT  = 60

# ── Supported interview domains ───────────────────────────────────────────────

INTERVIEW_DOMAINS = {
    "cognitive":    "Cognitive rehabilitation and reasoning assessment",
    "memory":       "Memory recall and retention evaluation",
    "behavioural":  "Behavioural and situational response interview",
    "technical":    "Technical problem-solving and logical reasoning",
    "general":      "General aptitude and communication skills",
}


# ── Groq chat helper ──────────────────────────────────────────────────────────

def _groq_chat(messages: list, temperature: float = 0.7, max_tokens: int = 512) -> Optional[str]:
    """
    Send a chat request to the Groq API via the OpenAI-compatible endpoint.
    Returns the assistant's response string, or None on failure.
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
            logger.error("[InterviewCoach] Groq API: invalid API key (401).")
            return None
        if resp.status_code == 429:
            logger.warning("[InterviewCoach] Groq rate limit (429). Retrying in 5s…")
            time.sleep(5)
            resp = requests.post(url, headers=headers, json=payload, timeout=GROQ_TIMEOUT)
            resp.raise_for_status()
        resp.raise_for_status()
        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        return text or None
    except requests.exceptions.Timeout:
        logger.error("[InterviewCoach] Groq API request timed out.")
        return None
    except requests.exceptions.ConnectionError as exc:
        logger.error("[InterviewCoach] Cannot reach Groq API: %s", exc)
        return None
    except Exception as exc:
        logger.error("[InterviewCoach] Groq API error: %s", exc)
        return None


# ── InterviewCoach ────────────────────────────────────────────────────────────

class InterviewCoach:
    """
    AI-powered mock interview coach for cognitive and professional preparation.

    Each session maintains its own conversation history and question bank.
    The coach adapts question difficulty based on user responses and tracks
    performance metrics across the session.

    Usage:
        coach = InterviewCoach()
        question = coach.start_session(session_id="user-123", domain="cognitive")
        feedback = coach.evaluate_response(session_id="user-123", response="My answer…")
        summary  = coach.end_session(session_id="user-123")
    """

    def __init__(self):
        self.sessions: dict[str, dict] = {}

    # ── Session lifecycle ─────────────────────────────────────────────────────

    def start_session(self, session_id: str, domain: str = "general") -> dict:
        """
        Initialise a new interview session for the given user.

        Args:
            session_id: Unique identifier for the user/session.
            domain: Interview domain key from INTERVIEW_DOMAINS.

        Returns:
            dict with 'question' (str) and 'session_id' (str).
        """
        domain = domain if domain in INTERVIEW_DOMAINS else "general"
        self.sessions[session_id] = {
            "domain":           domain,
            "history":          [],
            "questions_asked":  0,
            "correct_count":    0,
            "score":            0,
            "feedback_log":     [],
        }
        first_question = self._generate_question(session_id)
        return {"session_id": session_id, "question": first_question, "domain": domain}

    def evaluate_response(self, session_id: str, response: str) -> dict:
        """
        Evaluate the user's answer and return structured feedback + next question.

        Args:
            session_id: Active session identifier.
            response: The user's answer text.

        Returns:
            dict with 'feedback' (str), 'score_delta' (int), 'next_question' (str | None).
        """
        if session_id not in self.sessions:
            return {"error": "Session not found. Please start a new interview session."}

        session = self.sessions[session_id]
        session["history"].append({"role": "user", "content": response})
        session["questions_asked"] += 1

        feedback = self._generate_feedback(session_id, response)
        score_delta = self._score_response(response, feedback)
        session["score"] += score_delta
        session["feedback_log"].append({"response": response, "feedback": feedback, "delta": score_delta})

        next_question = None
        if session["questions_asked"] < 10:
            next_question = self._generate_question(session_id)

        return {
            "feedback":      feedback,
            "score_delta":   score_delta,
            "total_score":   session["score"],
            "next_question": next_question,
            "questions_done": session["questions_asked"],
        }

    def end_session(self, session_id: str) -> dict:
        """
        Conclude the session and return a performance summary.

        Args:
            session_id: Active session identifier.

        Returns:
            dict with 'total_score', 'questions_asked', 'summary' (str), 'feedback_log'.
        """
        if session_id not in self.sessions:
            return {"error": "Session not found."}

        session = self.sessions.pop(session_id)
        summary = self._generate_summary(session)

        return {
            "total_score":     session["score"],
            "questions_asked": session["questions_asked"],
            "domain":          session["domain"],
            "summary":         summary,
            "feedback_log":    session["feedback_log"],
        }

    def get_session_status(self, session_id: str) -> dict:
        """Return current session stats without ending the session."""
        if session_id not in self.sessions:
            return {"error": "Session not found."}
        s = self.sessions[session_id]
        return {
            "session_id":      session_id,
            "domain":          s["domain"],
            "questions_asked": s["questions_asked"],
            "score":           s["score"],
            "active":          True,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_system_prompt(self, domain: str) -> str:
        domain_desc = INTERVIEW_DOMAINS.get(domain, INTERVIEW_DOMAINS["general"])
        return (
            f"You are Synaptia's Interview Coach — a professional, encouraging, and insightful "
            f"interviewer specialising in: {domain_desc}. "
            "Your role is to:\n"
            "1. Ask one clear, focused question at a time.\n"
            "2. Provide specific, actionable feedback on each answer.\n"
            "3. Adapt question difficulty based on the user's performance.\n"
            "4. Maintain a supportive, professional tone — never dismissive.\n"
            "5. Keep responses concise and structured."
        )

    def _generate_question(self, session_id: str) -> str:
        """Generate the next interview question based on session history."""
        session = self.sessions[session_id]
        system = self._build_system_prompt(session["domain"])
        q_num = session["questions_asked"] + 1

        history_context = ""
        if session["history"]:
            last_pairs = session["history"][-4:]
            history_context = "\n".join(
                f"{m['role'].capitalize()}: {m['content']}" for m in last_pairs
            )

        user_prompt = (
            f"Ask interview question #{q_num} for a {session['domain']} interview. "
            f"{'This is the opening question — make it welcoming and foundational.' if q_num == 1 else ''}"
            f"{'Previous exchange:\n' + history_context if history_context else ''}"
            "\nReturn ONLY the question text, nothing else."
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_prompt},
        ]
        result = _groq_chat(messages, temperature=0.8, max_tokens=200)
        question = result or f"Question {q_num}: Can you describe your approach to problem-solving under cognitive load?"
        session["history"].append({"role": "assistant", "content": question})
        return question

    def _generate_feedback(self, session_id: str, response: str) -> str:
        """Generate structured feedback for a user's answer."""
        session = self.sessions[session_id]
        system = self._build_system_prompt(session["domain"])

        last_question = ""
        for msg in reversed(session["history"]):
            if msg["role"] == "assistant":
                last_question = msg["content"]
                break

        user_prompt = (
            f"The interviewee answered the following question:\n"
            f"Question: {last_question}\n"
            f"Answer: {response}\n\n"
            "Provide brief, specific feedback in 2-3 sentences: "
            "what was strong, what could be improved, and one concrete tip."
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_prompt},
        ]
        result = _groq_chat(messages, temperature=0.6, max_tokens=300)
        return result or "Good effort! Try to structure your answers using the STAR method for clarity."

    def _score_response(self, response: str, feedback: str) -> int:
        """
        Heuristic scoring: 0–10 points per response.
        A full AI-based scorer can replace this in a future iteration.
        """
        word_count = len(response.split())
        if word_count < 5:
            return 1
        if word_count < 20:
            return 4
        if word_count < 60:
            return 7
        return 10

    def _generate_summary(self, session: dict) -> str:
        """Generate a final performance summary for the ended session."""
        total    = session["questions_asked"]
        score    = session["score"]
        max_score = total * 10
        pct      = round((score / max_score * 100) if max_score > 0 else 0)

        system = self._build_system_prompt(session["domain"])
        user_prompt = (
            f"The candidate just completed a {session['domain']} interview with {total} questions. "
            f"Their total score was {score}/{max_score} ({pct}%). "
            "Write a warm, professional 2-3 sentence closing summary highlighting their overall "
            "performance and one key area to develop further."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_prompt},
        ]
        result = _groq_chat(messages, temperature=0.6, max_tokens=200)
        return result or (
            f"You completed {total} questions with a score of {score}/{max_score} ({pct}%). "
            "Keep practising structured responses — you're making solid progress!"
        )
