"""Academic vocabulary — the shared source for both layers of the V1.5 fix.

Two consumers:
- config.build_stt() biases Deepgram nova-3 toward these terms via keyterm
  prompting, preventing many mishearings at the source.
- normalizer.normalize() / looks_academic() use the per-session list to decide
  when to correct a transcript and as reference context for the correction.

BASE_LEXICON is curated and meant to be hand-edited. build_keyterms() extends it
per session with the student's own weak-topic names so boosting targets what they
actually study.
"""

# Curated base — terms Indian Class 6-12 / JEE / NEET students actually say,
# including Hindi science vocabulary and English<->Hindi code-mixed forms.
BASE_LEXICON: dict[str, list[str]] = {
    "trigonometry": [
        "sine", "cosine", "tangent", "cosec", "cosecant", "secant",
        "cotangent", "theta", "sin theta", "cos theta", "tan theta",
    ],
    "calculus": [
        "derivative", "differentiation", "avkalan", "integration",
        "samakalan", "integral", "limit", "function",
    ],
    "algebra": [
        "quadratic", "polynomial", "logarithm", "exponent", "coefficient",
    ],
    "physics_en": [
        "velocity", "acceleration", "displacement", "momentum", "torque",
        "angular velocity", "perpendicular", "amplitude", "frequency",
    ],
    "physics_hi": [
        "veg", "tvaran", "visthapan", "lambit karan", "balaghurnan",
    ],
    "chemistry": [
        "electrophile", "nucleophile", "SN1", "SN2", "isomer", "valency",
        "covalent", "molarity", "mole",
    ],
}

# Sent to Deepgram nova-3 as keyterms. Deliberately a TIGHT, high-value subset of
# the lexicon — the benchmark (benchmarks/RESULTS.md) showed that a large (~40+ term)
# keyterm list reproducibly makes nova-3 drop whole utterances to empty
# (e.g. "lambit karan ..." -> ""), while this ~15-term list keeps the same recovery
# with ZERO regressions on the production app voice. Keep this list short.
HIGH_VALUE_KEYTERMS = [
    "sin", "cos", "tan", "cosec", "theta",
    "avkalan", "samakalan", "derivative",
    "tvaran", "veg", "visthapan", "lambit karan", "torque",
    "electrophile", "nucleophile",
]

# Hard cap on the keyterm request — kept low on purpose (see above). Leaves room for
# a handful of per-student weak-topic names without entering the drop-prone range.
_KEYTERM_CAP = 25


def all_terms() -> list[str]:
    """Flat curated lexicon — used by the normalizer's gate and as LLM context."""
    terms: list[str] = []
    for group in BASE_LEXICON.values():
        terms.extend(group)
    return terms


def build_keyterms(profile: dict) -> list[str]:
    """The high-value keyterm core sent to the STT.

    Only the mishearing-prone academic terms are sent — NOT the full lexicon, and
    NOT the student's weak-topic names. Both were benchmarked and found to make
    nova-3 drop whole utterances to empty: notably the multi-word weak-topic names
    (e.g. "Organic Chemistry", "Rotational Motion") reproducibly killed transcripts
    that the bare core transcribes perfectly (see benchmarks/RESULTS.md). `profile`
    is accepted for forward-compatibility but intentionally not used to extend the
    keyterms — the profile still drives the prompt, memory, and the normalizer.
    """
    seen: set[str] = set()
    out: list[str] = []
    for term in HIGH_VALUE_KEYTERMS:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            out.append(term)
    return out[:_KEYTERM_CAP]
