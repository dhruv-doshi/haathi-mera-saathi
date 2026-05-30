"""Lightweight conversation state for Haathi Mera Saathi.

Holds the four fields the LLM updates via the set_session_state tool.
Re-injected into every LLM turn so the model always knows where it is.
"""

from dataclasses import dataclass, field


VALID_MODES = {
    "greeting",
    "doubt_solving",
    "topic_planning",
    "exam_strategy",
    "concept_reinforcement",
    "motivation",
    "energize_reset",
    "personal_support",
    "escalation",
}


@dataclass
class SessionState:
    mode: str = "greeting"
    subject: str = ""
    mood: str = "neutral"
    last_intent: str = ""

    def update(self, mode: str = "", subject: str = "", mood: str = "", last_intent: str = "") -> None:
        if mode and mode in VALID_MODES:
            self.mode = mode
        if subject:
            self.subject = subject
        if mood:
            self.mood = mood
        if last_intent:
            self.last_intent = last_intent

    def format(self) -> str:
        parts = [f"mode={self.mode}", f"mood={self.mood}"]
        if self.subject:
            parts.append(f"subject={self.subject}")
        if self.last_intent:
            parts.append(f"last_intent={self.last_intent}")
        return "[Session state: " + ", ".join(parts) + "]"
