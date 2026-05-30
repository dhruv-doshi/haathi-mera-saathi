"""Offline checks for the deterministic safety layer (src/safety.py).

Self-contained (no pytest, no API key — the detector is LLM-free). Run it:

    .venv/bin/python tests/test_safety.py

Covers: positive detection across self-harm / abuse / distress in English,
Hinglish, and Hindi; negatives that must NOT fire (academic/idiomatic); and the
guarantee that the spoken helpline line always carries the number 14416.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import safety  # noqa: E402

# (transcript, expected_category_or_None)
DETECT_CASES = [
    # self-harm
    ("I want to kill myself", "self_harm"),
    ("honestly I don't want to live anymore", "self_harm"),
    ("mujhe lagta hai main marna chahta hoon", "self_harm"),
    ("ab jeena nahi chahta yaar", "self_harm"),
    ("I keep cutting myself", "self_harm"),
    ("I've been thinking about suicide", "self_harm"),
    # abuse
    ("my dad hits me every night", "abuse"),
    ("ghar mein maarte hain mujhe roz", "abuse"),
    ("someone touched me and I didn't like it", "abuse"),
    # distress
    ("I feel hopeless and worthless", "distress"),
    ("I can't go on like this", "distress"),
    ("everyone would be better off without me", "distress"),
    # negatives — must NOT trigger
    ("the cut-off for JEE is high this year", None),
    ("this chapter is killing me lol", None),
    ("bhai mai thak gaya hoon, dead tired", None),
    ("sir ne marks kaat liye mere", None),
    ("haan theek hai chalo padhte hain", None),
    ("I'm dying to finish this syllabus", None),
    ("organic chemistry is hopeless to memorize", None),  # not self-referential
    ("", None),
]


def test_detect() -> int:
    failures = 0
    for text, expected in DETECT_CASES:
        got = safety.detect_distress(text)
        ok = got == expected
        print(f"  [{'PASS' if ok else 'FAIL'}] detect_distress({text!r}) = {got} (want {expected})")
        failures += not ok
    return failures


def test_helpline() -> int:
    failures = 0
    for pref in ("Hinglish", "English", "Hindi", "", None):
        line = safety.helpline_line(pref)
        ok = "14416" in line
        print(f"  [{'PASS' if ok else 'FAIL'}] helpline_line({pref!r}) contains 14416")
        failures += not ok
    # The escalation directive must also name the helpline.
    ok = "14416" in safety.ESCALATION_DIRECTIVE
    print(f"  [{'PASS' if ok else 'FAIL'}] ESCALATION_DIRECTIVE contains 14416")
    failures += not ok
    return failures


def main() -> None:
    print("Distress detection (offline):")
    failures = test_detect()
    print("\nHelpline guarantee (offline):")
    failures += test_helpline()

    print()
    if failures:
        print(f"FAILED: {failures} check(s) failed")
        sys.exit(1)
    print("All checks passed")


if __name__ == "__main__":
    main()
