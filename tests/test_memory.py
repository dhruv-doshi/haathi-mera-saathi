"""Offline checks for the accumulating memory store + profile merge.

Self-contained (no pytest). Uses a temporary memory dir so it never touches real
data. Run it:

    .venv/bin/python tests/test_memory.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import memory  # noqa: E402
import profile as profile_mod  # noqa: E402


def _fresh_backend(tmp: Path) -> memory.LocalMemory:
    memory.MEMORY_DIR = tmp  # redirect all file I/O to the temp dir
    return memory.LocalMemory()


def test_legacy_migration() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        # Write a legacy bare-summary file.
        (tmp / "stu.json").write_text(json.dumps({"summary": "old single summary"}))
        m = _fresh_backend(tmp)

        recent = m.get_recent("stu", 5)
        ok = len(recent) == 1 and recent[0]["summary"] == "old single summary"
        print(f"  [{'PASS' if ok else 'FAIL'}] legacy summary migrates to one session entry")
        failures += not ok

        ok = recent[0]["source"] == "heuristic"
        print(f"  [{'PASS' if ok else 'FAIL'}] migrated entry tagged source=heuristic")
        failures += not ok

        ok = m.get_summary("stu") == "old single summary"
        print(f"  [{'PASS' if ok else 'FAIL'}] get_summary returns newest summary")
        failures += not ok
    return failures


def test_accumulation() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as d:
        m = _fresh_backend(Path(d))
        m.append_session("stu", {"summary": "s1", "mode": "doubt_solving"})
        m.append_session("stu", {"summary": "s2", "mode": "exam_strategy"})
        m.append_session("stu", {"summary": "s3"})

        hist = m.get_history("stu")
        ok = [h["summary"] for h in hist] == ["s1", "s2", "s3"]
        print(f"  [{'PASS' if ok else 'FAIL'}] append_session accumulates (no overwrite)")
        failures += not ok

        recent = m.get_recent("stu", 2)
        ok = [r["summary"] for r in recent] == ["s3", "s2"]
        print(f"  [{'PASS' if ok else 'FAIL'}] get_recent returns newest-first, capped to n")
        failures += not ok

        ok = bool(hist[0]["ts"])
        print(f"  [{'PASS' if ok else 'FAIL'}] entries are timestamped")
        failures += not ok

        m.update_last_session("stu", {"summary": "s3-upgraded", "source": "llm"})
        last = m.get_recent("stu", 1)[0]
        ok = last["summary"] == "s3-upgraded" and last["source"] == "llm"
        print(f"  [{'PASS' if ok else 'FAIL'}] update_last_session upgrades newest entry in place")
        failures += not ok

        m.save_learned("stu", {**memory.empty_learned(), "weak_topics": ["Thermo"]})
        ok = m.get_learned("stu")["weak_topics"] == ["Thermo"]
        print(f"  [{'PASS' if ok else 'FAIL'}] learned block round-trips")
        failures += not ok
        # ...and is preserved across a later session append.
        m.append_session("stu", {"summary": "s4"})
        ok = m.get_learned("stu")["weak_topics"] == ["Thermo"]
        print(f"  [{'PASS' if ok else 'FAIL'}] learned block survives new sessions")
        failures += not ok
    return failures


def test_profile_merge() -> int:
    failures = 0
    seed = {
        "name": "Aarav", "class": 11, "track": "JEE", "language_pref": "Hinglish",
        "weak_topics": ["Organic Chemistry", "Rotational Motion"],
        "strong_topics": ["Algebra"],
        "last_scores": [{"test": "Mock 4", "subject": "Physics", "score": "48/120"}],
        "syllabus_progress": {"Physics": "60%"},
        "next_exam": {"name": "JEE Mains", "days_away": 15},
    }
    learned = {
        **memory.empty_learned(),
        "weak_topics": ["Thermodynamics"],
        "strong_topics": ["algebra"],  # case-dup of seed -> must not duplicate
        "resolved_weak_topics": ["Rotational Motion"],  # seed weak -> removed
        "scores": [{"test": "Mock 5", "subject": "Physics", "score": "62/120"}],
        "commitments": ["redo SN1/SN2 set"],
    }
    merged = profile_mod.merge_learned(seed, learned)

    ok = merged["weak_topics"] == ["Organic Chemistry", "Thermodynamics"]
    print(f"  [{'PASS' if ok else 'FAIL'}] merge unions weak + removes resolved seed topic")
    failures += not ok

    ok = merged["strong_topics"] == ["Algebra"]
    print(f"  [{'PASS' if ok else 'FAIL'}] merge dedups strong topics case-insensitively")
    failures += not ok

    ok = merged["last_scores"][-1]["score"] == "62/120"
    print(f"  [{'PASS' if ok else 'FAIL'}] learned score appended as newest")
    failures += not ok

    # seed must be untouched (non-destructive)
    ok = seed["weak_topics"] == ["Organic Chemistry", "Rotational Motion"]
    print(f"  [{'PASS' if ok else 'FAIL'}] merge does not mutate the seed dict")
    failures += not ok

    out = profile_mod.format_profile(seed, learned)
    ok = "Thermodynamics" in out and "Rotational Motion" not in out and "redo SN1/SN2" in out
    print(f"  [{'PASS' if ok else 'FAIL'}] format_profile reflects learned layer")
    failures += not ok
    return failures


def main() -> None:
    print("Legacy migration (offline):")
    failures = test_legacy_migration()
    print("\nAccumulation (offline):")
    failures += test_accumulation()
    print("\nProfile merge (offline):")
    failures += test_profile_merge()

    print()
    if failures:
        print(f"FAILED: {failures} check(s) failed")
        sys.exit(1)
    print("All checks passed")


if __name__ == "__main__":
    main()
