"""Checks for the learnings engine (src/learnings.py).

Self-contained (no pytest). The reducer + JSON-parse checks run fully offline.
The live extract_learnings() check only runs when OPENROUTER_API_KEY is set.

    .venv/bin/python tests/test_learnings.py
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import learnings  # noqa: E402
import memory  # noqa: E402


def test_reducer() -> int:
    failures = 0

    # Accumulate + dedup weak topics; resolve removes a prior weak topic.
    existing = memory.empty_learned()
    existing["weak_topics"] = ["Organic Chemistry", "Rotational Motion"]
    extracted = {
        "new_weak_topics": ["organic chemistry", "Thermodynamics"],  # dup (case)
        "resolved_weak_topics": ["Rotational Motion"],
        "new_strong_topics": ["Algebra"],
        "scores": [{"test": "Mock 5", "subject": "Physics", "score": "60/120"}],
        "commitments": ["redo SN1/SN2 set"],
        "notes": ["feeling more confident in mechanics"],
    }
    out = learnings.update_learned(existing, extracted)

    cases = [
        ("weak dedup + resolved removed",
         out["weak_topics"] == ["Organic Chemistry", "Thermodynamics"]),
        ("strong added", out["strong_topics"] == ["Algebra"]),
        ("score appended", out["scores"] == extracted["scores"]),
        ("commitment appended", out["commitments"] == ["redo SN1/SN2 set"]),
        ("note appended", out["notes"] == extracted["notes"]),
        ("updated_at stamped", bool(out["updated_at"])),
    ]
    for label, ok in cases:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        failures += not ok

    # List caps: pushing >10 commitments keeps only the last 10.
    big = memory.empty_learned()
    big["commitments"] = [f"c{i}" for i in range(9)]
    out2 = learnings.update_learned(big, {"commitments": ["c9", "c10", "c11"]})
    ok = len(out2["commitments"]) == 10 and out2["commitments"][-1] == "c11"
    print(f"  [{'PASS' if ok else 'FAIL'}] commitments capped at 10, newest kept")
    failures += not ok

    # Empty extraction must not corrupt existing state.
    out3 = learnings.update_learned(existing, {})
    ok = out3["weak_topics"] == ["Organic Chemistry", "Rotational Motion"]
    print(f"  [{'PASS' if ok else 'FAIL'}] empty extraction preserves weak topics")
    failures += not ok
    return failures


def test_parse_helpers() -> int:
    failures = 0
    fenced = '```json\n{"summary": "ok", "notes": ["a"]}\n```'
    parsed = learnings._coerce(__import__("json").loads(learnings._strip_fences(fenced)))
    ok = parsed["summary"] == "ok" and parsed["notes"] == ["a"]
    print(f"  [{'PASS' if ok else 'FAIL'}] strip_fences + coerce handles ```json``` wrapper")
    failures += not ok

    # _coerce fills missing keys with [] and coerces non-lists.
    c = learnings._coerce({"summary": 123, "new_weak_topics": "nope"})
    ok = c["summary"] == "123" and c["new_weak_topics"] == [] and c["notes"] == []
    print(f"  [{'PASS' if ok else 'FAIL'}] coerce normalizes bad shapes")
    failures += not ok
    return failures


async def test_extract_live() -> int:
    import config

    llm = config.build_learnings_llm()
    transcript = (
        "assistant: Aarav, let's tackle Organic today.\n"
        "user: haan sir, SN1 SN2 ab samajh aa gaya, but thermodynamics is killing me.\n"
        "assistant: great progress on substitution! We'll hit thermo next.\n"
        "user: ok I'll redo the SN1 problem set tonight."
    )
    out = await learnings.extract_learnings(transcript, llm, timeout=8.0)
    ok = isinstance(out, dict) and "summary" in out and isinstance(out["notes"], list)
    print(f"  [{'PASS' if ok else 'FAIL'}] extract_learnings returns a well-formed dict")
    print(f"        -> {out}")
    return 0 if ok else 1


def main() -> None:
    print("Reducer (offline):")
    failures = test_reducer()
    print("\nParse helpers (offline):")
    failures += test_parse_helpers()

    if os.environ.get("OPENROUTER_API_KEY"):
        print("\nExtraction (live, fast model):")
        failures += asyncio.run(test_extract_live())
    else:
        print("\nExtraction (live): SKIPPED — set OPENROUTER_API_KEY to run")

    print()
    if failures:
        print(f"FAILED: {failures} check(s) failed")
        sys.exit(1)
    print("All checks passed")


if __name__ == "__main__":
    main()
