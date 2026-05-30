"""Session memory interface.

Memory ACCUMULATES across sessions. Each session appends one entry to a history
list; nothing is overwritten. A separate `learned` block holds the durable,
LLM-extracted deltas (new weak/strong topics, scores, commitments) that are
merged with the static profile when building the next session's prompt — the
profile seed (profiles/<id>.json) is never mutated.

Operations:
  get_summary(student_id)        → newest session summary, or "" if none
  save_summary(student_id, txt)  → append a heuristic session entry
  append_session(student_id, e)  → append one (timestamped) session entry
  get_recent(student_id, n)      → last n session entries, newest first
  get_history(student_id)        → all session entries (oldest first)
  get_learned(student_id)        → the durable learned-delta block
  save_learned(student_id, d)    → replace the learned-delta block

File schema (memory/<student_id>.json), schema_version = 2:
  {
    "schema_version": 2,
    "sessions": [{"ts", "summary", "mode", "mood", "subject",
                  "last_intent", "source"}],
    "learned":  {"weak_topics", "strong_topics", "scores",
                 "commitments", "notes", "updated_at"}
  }

Backward compatible: a legacy {"summary": "..."} file is migrated lazily into a
single synthetic session entry on read (the file is only rewritten on next save).

Default backend: local JSON file at memory/<student_id>.json  (no paid credits).
Optional backend: Maximem Synap, enabled by setting MEMORY_BACKEND = "synap" in
config.py. No Synap network calls are made unless that flag is on.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import config

MEMORY_DIR = Path(__file__).parent.parent / "memory"

SCHEMA_VERSION = 2

# Session-entry fields, with their defaults. append_session() normalizes every
# entry to exactly these keys so the history stays uniform.
_SESSION_FIELDS = {
    "ts": "",
    "summary": "",
    "mode": "",
    "mood": "",
    "subject": "",
    "last_intent": "",
    "source": "heuristic",  # "heuristic" | "llm"
}


def empty_learned() -> dict:
    """The shape of an empty learned-delta block."""
    return {
        "weak_topics": [],
        "strong_topics": [],
        "resolved_weak_topics": [],  # cleared topics — removed from the seed at merge
        "scores": [],
        "commitments": [],
        "notes": [],
        "updated_at": "",
    }


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _migrate(data: dict) -> dict:
    """Return a v2 store dict, upgrading the legacy {"summary": "..."} shape.

    Pure (does not touch disk). A bare legacy summary becomes one synthetic
    heuristic session entry so accumulated history starts from it.
    """
    if data.get("schema_version") == SCHEMA_VERSION:
        data.setdefault("sessions", [])
        data.setdefault("learned", empty_learned())
        return data

    store = {"schema_version": SCHEMA_VERSION, "sessions": [], "learned": empty_learned()}
    legacy = (data.get("summary") or "").strip()
    if legacy:
        entry = dict(_SESSION_FIELDS)
        entry["summary"] = legacy
        entry["source"] = "heuristic"
        store["sessions"].append(entry)
    return store


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

class MemoryBackend(ABC):
    @abstractmethod
    def get_summary(self, student_id: str) -> str: ...

    @abstractmethod
    def save_summary(self, student_id: str, summary: str) -> None: ...

    @abstractmethod
    def append_session(self, student_id: str, entry: dict) -> None: ...

    @abstractmethod
    def update_last_session(self, student_id: str, fields: dict) -> None: ...

    @abstractmethod
    def get_recent(self, student_id: str, n: int = 1) -> list[dict]: ...

    @abstractmethod
    def get_history(self, student_id: str) -> list[dict]: ...

    @abstractmethod
    def get_learned(self, student_id: str) -> dict: ...

    @abstractmethod
    def save_learned(self, student_id: str, learned: dict) -> None: ...


# ---------------------------------------------------------------------------
# Local JSON implementation
# ---------------------------------------------------------------------------

class LocalMemory(MemoryBackend):
    def __init__(self):
        MEMORY_DIR.mkdir(exist_ok=True)

    def _path(self, student_id: str) -> Path:
        return MEMORY_DIR / f"{student_id}.json"

    def _load(self, student_id: str) -> dict:
        """Read + lazily migrate. Returns a fresh v2 store if no file exists."""
        p = self._path(student_id)
        if not p.exists():
            return {"schema_version": SCHEMA_VERSION, "sessions": [], "learned": empty_learned()}
        with open(p) as f:
            data = json.load(f)
        return _migrate(data)

    def _write(self, student_id: str, data: dict) -> None:
        with open(self._path(student_id), "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_summary(self, student_id: str) -> str:
        sessions = self._load(student_id)["sessions"]
        return sessions[-1]["summary"] if sessions else ""

    def save_summary(self, student_id: str, summary: str) -> None:
        # Kept for backward compatibility: now accumulates instead of overwriting.
        self.append_session(student_id, {"summary": summary, "source": "heuristic"})

    def append_session(self, student_id: str, entry: dict) -> None:
        store = self._load(student_id)
        normalized = dict(_SESSION_FIELDS)
        normalized.update({k: v for k, v in entry.items() if k in _SESSION_FIELDS})
        if not normalized["ts"]:
            normalized["ts"] = _now()
        store["sessions"].append(normalized)
        self._write(student_id, store)

    def update_last_session(self, student_id: str, fields: dict) -> None:
        """Patch the most recent session entry in place (e.g. upgrade a
        heuristic summary to an LLM one). No-op if there is no history."""
        store = self._load(student_id)
        if not store["sessions"]:
            return
        last = store["sessions"][-1]
        last.update({k: v for k, v in fields.items() if k in _SESSION_FIELDS})
        self._write(student_id, store)

    def get_recent(self, student_id: str, n: int = 1) -> list[dict]:
        sessions = self._load(student_id)["sessions"]
        if n <= 0:
            return []
        return list(reversed(sessions[-n:]))

    def get_history(self, student_id: str) -> list[dict]:
        return self._load(student_id)["sessions"]

    def get_learned(self, student_id: str) -> dict:
        learned = self._load(student_id).get("learned") or {}
        merged = empty_learned()
        merged.update(learned)
        return merged

    def save_learned(self, student_id: str, learned: dict) -> None:
        store = self._load(student_id)
        store["learned"] = learned
        self._write(student_id, store)


# ---------------------------------------------------------------------------
# Maximem Synap implementation (disabled unless MEMORY_BACKEND = "synap")
# ---------------------------------------------------------------------------

class SynapMemory(MemoryBackend):
    """Persistent cross-session memory via Maximem Synap.

    Enabled by setting MEMORY_BACKEND = "synap" in config.py and providing
    SYNAP_API_KEY in .env.local. No network calls are made unless this backend
    is selected.
    """

    def __init__(self):
        import os
        self._api_key = os.environ.get("SYNAP_API_KEY", "")
        if not self._api_key:
            raise RuntimeError("SYNAP_API_KEY missing — set it in .env.local")

    def get_summary(self, student_id: str) -> str:
        raise NotImplementedError("Synap get_summary not yet wired")

    def save_summary(self, student_id: str, summary: str) -> None:
        raise NotImplementedError("Synap save_summary not yet wired")

    def append_session(self, student_id: str, entry: dict) -> None:
        raise NotImplementedError("Synap append_session not yet wired")

    def update_last_session(self, student_id: str, fields: dict) -> None:
        raise NotImplementedError("Synap update_last_session not yet wired")

    def get_recent(self, student_id: str, n: int = 1) -> list[dict]:
        raise NotImplementedError("Synap get_recent not yet wired")

    def get_history(self, student_id: str) -> list[dict]:
        raise NotImplementedError("Synap get_history not yet wired")

    def get_learned(self, student_id: str) -> dict:
        raise NotImplementedError("Synap get_learned not yet wired")

    def save_learned(self, student_id: str, learned: dict) -> None:
        raise NotImplementedError("Synap save_learned not yet wired")


# ---------------------------------------------------------------------------
# Factory — calling code never touches backend selection
# ---------------------------------------------------------------------------

def build_memory() -> MemoryBackend:
    if config.MEMORY_BACKEND == "synap":
        return SynapMemory()
    return LocalMemory()


# ---------------------------------------------------------------------------
# Module-level singleton — import and use directly
# ---------------------------------------------------------------------------

_backend: MemoryBackend | None = None


def _b() -> MemoryBackend:
    global _backend
    if _backend is None:
        _backend = build_memory()
    return _backend


def get_summary(student_id: str) -> str:
    return _b().get_summary(student_id)


def save_summary(student_id: str, summary: str) -> None:
    _b().save_summary(student_id, summary)


def append_session(student_id: str, entry: dict) -> None:
    _b().append_session(student_id, entry)


def update_last_session(student_id: str, fields: dict) -> None:
    _b().update_last_session(student_id, fields)


def get_recent(student_id: str, n: int = 1) -> list[dict]:
    return _b().get_recent(student_id, n)


def get_history(student_id: str) -> list[dict]:
    return _b().get_history(student_id)


def get_learned(student_id: str) -> dict:
    return _b().get_learned(student_id)


def save_learned(student_id: str, learned: dict) -> None:
    _b().save_learned(student_id, learned)
