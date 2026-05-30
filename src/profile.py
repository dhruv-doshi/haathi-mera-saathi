"""Student profile loader and context formatter.

load_profile(id)  → raw dict from profiles/<id>.json (a frozen, hand-authored seed)
format_profile(profile, learned) → short context string for the system prompt,
    merging the static seed with the LLM-learned delta layer (see merge_learned).

The seed JSON is never mutated. Everything the mentor learns lives in the memory
`learned` block and is merged in here, fresh, each session.
"""

import json
from pathlib import Path

PROFILES_DIR = Path(__file__).parent.parent / "profiles"


def load_profile(profile_id: str) -> dict:
    path = PROFILES_DIR / f"{profile_id}.json"
    with open(path) as f:
        return json.load(f)


def _dedup_ci(items) -> list:
    """Case-insensitive dedup of strings, preserving first-seen order."""
    seen, out = set(), []
    for it in items:
        s = str(it).strip()
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


def merge_learned(p: dict, learned: dict | None) -> dict:
    """Return a shallow copy of the seed profile with the learned delta folded in.

    Non-destructive: weak/strong topics are unioned (case-insensitive), resolved
    weak topics are dropped (from seed too), and learned scores are appended so
    format_profile's "last score" naturally reflects the newest one.
    """
    merged = dict(p)
    if not learned:
        return merged

    resolved = learned.get("resolved_weak_topics") or []
    drop = {str(r).strip().lower() for r in resolved}
    weak = _dedup_ci(list(p.get("weak_topics") or []) + list(learned.get("weak_topics") or []))
    merged["weak_topics"] = [t for t in weak if t.lower() not in drop]
    merged["strong_topics"] = _dedup_ci(
        list(p.get("strong_topics") or []) + list(learned.get("strong_topics") or [])
    )
    if learned.get("scores"):
        merged["last_scores"] = list(p.get("last_scores") or []) + list(learned["scores"])
    return merged


def format_profile(p: dict, learned: dict | None = None) -> str:
    p = merge_learned(p, learned)

    weak = ", ".join(p["weak_topics"]) if p["weak_topics"] else "none flagged"
    strong = ", ".join(p["strong_topics"]) if p["strong_topics"] else "none flagged"

    scores = ""
    if p.get("last_scores"):
        s = p["last_scores"][-1]
        scores = f"Last score: {s['subject']} {s['test']} — {s['score']}."

    progress = ", ".join(f"{subj} {pct}" for subj, pct in p["syllabus_progress"].items())

    exam = ""
    if p.get("next_exam"):
        e = p["next_exam"]
        exam = f"Next exam: {e['name']} in {e['days_away']} days."

    # Durable personal context the mentor picked up in past sessions.
    extra = ""
    if learned:
        bits = list(learned.get("commitments") or []) + list(learned.get("notes") or [])
        if bits:
            extra = " Recently: " + "; ".join(bits[:4]) + "."

    return (
        f"Student: {p['name']}, Class {p['class']}, {p['track']} track. "
        f"Language: {p['language_pref']}. "
        f"Weak topics: {weak}. Strong: {strong}. "
        f"{scores} "
        f"Syllabus progress: {progress}. "
        f"{exam}"
        f"{extra}"
    ).strip()
