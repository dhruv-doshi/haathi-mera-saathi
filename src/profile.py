"""Student profile loader and context formatter.

load_profile(id)  → raw dict from profiles/<id>.json
format_profile(profile) → short, human-readable context string for the system prompt
"""

import json
from pathlib import Path

PROFILES_DIR = Path(__file__).parent.parent / "profiles"


def load_profile(profile_id: str) -> dict:
    path = PROFILES_DIR / f"{profile_id}.json"
    with open(path) as f:
        return json.load(f)


def format_profile(p: dict) -> str:
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

    return (
        f"Student: {p['name']}, Class {p['class']}, {p['track']} track. "
        f"Language: {p['language_pref']}. "
        f"Weak topics: {weak}. Strong: {strong}. "
        f"{scores} "
        f"Syllabus progress: {progress}. "
        f"{exam}"
    ).strip()
