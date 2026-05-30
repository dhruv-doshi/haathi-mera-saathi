"""Session memory interface.

Two operations:
  get_summary(student_id)       → prior-session summary string, or "" if none
  save_summary(student_id, txt) → persist a short end-of-session summary

Default backend: local JSON file at memory/<student_id>.json  (no paid credits).
Optional backend: Maximem Synap, enabled by setting MEMORY_BACKEND = "synap" in
config.py. No Synap network calls are made unless that flag is on.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

import config

MEMORY_DIR = Path(__file__).parent.parent / "memory"


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

class MemoryBackend(ABC):
    @abstractmethod
    def get_summary(self, student_id: str) -> str: ...

    @abstractmethod
    def save_summary(self, student_id: str, summary: str) -> None: ...


# ---------------------------------------------------------------------------
# Local JSON implementation
# ---------------------------------------------------------------------------

class LocalMemory(MemoryBackend):
    def __init__(self):
        MEMORY_DIR.mkdir(exist_ok=True)

    def _path(self, student_id: str) -> Path:
        return MEMORY_DIR / f"{student_id}.json"

    def get_summary(self, student_id: str) -> str:
        p = self._path(student_id)
        if not p.exists():
            return ""
        with open(p) as f:
            data = json.load(f)
        return data.get("summary", "")

    def save_summary(self, student_id: str, summary: str) -> None:
        p = self._path(student_id)
        existing = {}
        if p.exists():
            with open(p) as f:
                existing = json.load(f)
        existing["summary"] = summary
        with open(p, "w") as f:
            json.dump(existing, f, indent=2)


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
        # Wire Synap SDK calls here when demoing cross-call memory.
        raise NotImplementedError("Synap get_summary not yet wired")

    def save_summary(self, student_id: str, summary: str) -> None:
        raise NotImplementedError("Synap save_summary not yet wired")


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


def get_summary(student_id: str) -> str:
    global _backend
    if _backend is None:
        _backend = build_memory()
    return _backend.get_summary(student_id)


def save_summary(student_id: str, summary: str) -> None:
    global _backend
    if _backend is None:
        _backend = build_memory()
    _backend.save_summary(student_id, summary)
