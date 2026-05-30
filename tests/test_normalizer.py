"""Golden-set verification for the V1.5 academic-term normalizer.

Self-contained (no pytest dependency — this repo stays lightweight). Run it:

    .venv/bin/python tests/test_normalizer.py

The looks_academic checks run fully offline. The live normalize() checks only
run when OPENROUTER_API_KEY is set, and exercise the real fast-model correction.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import lexicon  # noqa: E402
import normalizer  # noqa: E402

LEXICON = lexicon.all_terms()

# (transcript, should_the_gate_fire)
GATE_CASES = [
    ("signs of thirty degree", True),
    ("kos theta nikalo", True),
    ("co sec x ka value kya hai", True),
    ("lambit karan nikalo", True),
    ("tvaran kya hoga is case mein", True),
    ("sin theta ka value 30 degree pe", True),
    ("haan theek hai chalo", False),      # casual -> must pass through
    ("bhai mai thak gaya hoon", False),   # casual -> must pass through
]

# (misheard input, substrings expected in the corrected output) — live only
NORMALIZE_CASES = [
    ("signs of thirty degrees", ["sin"]),
    ("kos theta", ["cos"]),
    ("co sec x", ["cosec"]),
]


def test_gate() -> int:
    failures = 0
    for text, expected in GATE_CASES:
        got = normalizer.looks_academic(text, LEXICON)
        ok = got == expected
        print(f"  [{'PASS' if ok else 'FAIL'}] looks_academic({text!r}) = {got} (want {expected})")
        failures += not ok
    return failures


async def test_normalize_live() -> int:
    import config

    llm = config.build_normalizer_llm()
    failures = 0
    for text, expected_substrs in NORMALIZE_CASES:
        out = await normalizer.normalize(text, LEXICON, llm, timeout=8.0)
        low = out.lower()
        ok = any(s in low for s in expected_substrs)
        print(f"  [{'PASS' if ok else 'FAIL'}] normalize({text!r}) -> {out!r} (want one of {expected_substrs})")
        failures += not ok
    return failures


def main() -> None:
    print("Gate (offline):")
    failures = test_gate()

    if os.environ.get("OPENROUTER_API_KEY"):
        print("\nNormalize (live, fast model):")
        failures += asyncio.run(test_normalize_live())
    else:
        print("\nNormalize (live): SKIPPED — set OPENROUTER_API_KEY to run")

    print()
    if failures:
        print(f"FAILED: {failures} check(s) failed")
        sys.exit(1)
    print("All checks passed")


if __name__ == "__main__":
    main()
