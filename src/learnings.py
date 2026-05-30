"""End-of-session learnings extraction — the self-updating-profile engine.

At session end, a fast model reads the conversation transcript and extracts
durable "learnings": topics that improved or regressed, scores mentioned, and
commitments the student made. These fold into the memory `learned` block (a
non-destructive delta layer) which is merged with the static profile seed when
building the next session's prompt — so the next call's opening reflects real
progress, without ever mutating profiles/<id>.json.

Two pieces, mirroring normalizer.py:
- extract_learnings(transcript, llm, timeout): one timeout-guarded model pass
  returning a parsed dict, or None on any failure (caller falls back to the
  heuristic summary). Never raises into shutdown.
- update_learned(existing, extracted): a pure, LLM-free reducer that folds an
  extraction into the persisted learned block (dedup + cap). Fully testable.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from livekit.agents import llm as _llm

import memory

logger = logging.getLogger("learnings")

_DEFAULT_TIMEOUT_S = 5.0

# Bound list growth in the persisted learned block.
_LIST_CAP = 10

_SYSTEM = (
    "You analyze a transcript of a voice call between an academic mentor and an "
    "Indian student (boards/JEE/NEET). Extract only DURABLE facts worth "
    "remembering for the next call. Output ONLY a single JSON object, no prose, "
    "no markdown fences, with exactly these keys:\n"
    '  "summary": one short sentence describing what happened this session.\n'
    '  "new_weak_topics": array of topics the student now struggles with.\n'
    '  "resolved_weak_topics": array of previously-weak topics that now seem ok.\n'
    '  "new_strong_topics": array of topics the student is now strong in.\n'
    '  "scores": array of {"test","subject","score"} the student mentioned.\n'
    '  "commitments": array of concrete things the student agreed to do next.\n'
    '  "notes": array of short, durable personal/contextual notes.\n'
    "Use [] for anything absent. Be conservative — do not invent. Keep topic "
    "names short (e.g. \"Organic Chemistry\", \"Rotational Motion\")."
)

_EXPECTED_KEYS = (
    "summary",
    "new_weak_topics",
    "resolved_weak_topics",
    "new_strong_topics",
    "scores",
    "commitments",
    "notes",
)


def _strip_fences(text: str) -> str:
    """Remove a ```json ... ``` wrapper if the model added one."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1] if "\n" in t else t
        if t.endswith("```"):
            t = t[: -len("```")]
        # drop a leading "json" language tag left on its own line
        if t.lower().startswith("json"):
            t = t[len("json"):]
    return t.strip()


def _coerce(raw: dict) -> dict:
    """Keep only expected keys with the right shapes; fill missing with defaults."""
    out: dict = {}
    out["summary"] = str(raw.get("summary") or "").strip()
    for key in _EXPECTED_KEYS:
        if key == "summary":
            continue
        val = raw.get(key)
        out[key] = val if isinstance(val, list) else []
    return out


async def extract_learnings(transcript: str, llm, timeout: float = _DEFAULT_TIMEOUT_S) -> dict | None:
    """Return a parsed learnings dict, or None on any failure/timeout/cancel."""
    if not transcript or not transcript.strip():
        return None
    try:
        ctx = _llm.ChatContext.empty()
        ctx.add_message(role="system", content=_SYSTEM)
        ctx.add_message(role="user", content=transcript)

        resp = await asyncio.wait_for(llm.chat(chat_ctx=ctx).collect(), timeout=timeout)
        text = _strip_fences(resp.text or "")
        if not text:
            return None
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            return None
        return _coerce(parsed)
    except asyncio.TimeoutError:
        logger.warning("learnings extraction timed out (%.0fms)", timeout * 1000)
        return None
    except asyncio.CancelledError:
        # Worker draining mid-extraction — caller already persisted the heuristic.
        logger.warning("learnings extraction cancelled during shutdown")
        return None
    except json.JSONDecodeError:
        logger.warning("learnings extraction returned non-JSON; skipping")
        return None
    except Exception:
        logger.exception("learnings extraction failed")
        return None


def _dedup(items: list) -> list:
    """Case-insensitive dedup of strings, preserving first-seen order."""
    seen: set[str] = set()
    out: list = []
    for item in items:
        s = str(item).strip()
        if not s:
            continue
        key = s.lower()
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


def _without(items: list, remove: list) -> list:
    """Drop entries (case-insensitive) that appear in `remove`."""
    drop = {str(r).strip().lower() for r in remove}
    return [i for i in items if str(i).strip().lower() not in drop]


def update_learned(existing: dict, extracted: dict) -> dict:
    """Fold an extraction into the persisted learned block. Pure (no I/O, no LLM).

    - weak_topics:   (existing ∪ new) minus resolved   (case-insensitive)
    - strong_topics: (existing ∪ new)                   (case-insensitive)
    - scores/commitments/notes: appended, capped to the most recent _LIST_CAP
    """
    base = memory.empty_learned()
    base.update(existing or {})
    ext = _coerce(extracted or {})

    weak = _dedup(list(base["weak_topics"]) + list(ext["new_weak_topics"]))
    weak = _without(weak, ext["resolved_weak_topics"])
    strong = _dedup(list(base["strong_topics"]) + list(ext["new_strong_topics"]))
    # Accumulate resolved topics so the merge can also clear matching SEED weak
    # topics; a topic flagged weak again this session drops out of resolved.
    resolved = _dedup(list(base["resolved_weak_topics"]) + list(ext["resolved_weak_topics"]))
    resolved = _without(resolved, ext["new_weak_topics"])

    return {
        "weak_topics": weak,
        "strong_topics": strong,
        "resolved_weak_topics": resolved,
        "scores": (list(base["scores"]) + list(ext["scores"]))[-_LIST_CAP:],
        "commitments": (list(base["commitments"]) + list(ext["commitments"]))[-_LIST_CAP:],
        "notes": (list(base["notes"]) + list(ext["notes"]))[-_LIST_CAP:],
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
