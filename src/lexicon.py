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

# Deepgram caps keyterm prompting; keep the request well under any limit.
_KEYTERM_CAP = 100


def all_terms() -> list[str]:
    """Flat curated lexicon — used by the normalizer's gate and as LLM context."""
    terms: list[str] = []
    for group in BASE_LEXICON.values():
        terms.extend(group)
    return terms


def build_keyterms(profile: dict) -> list[str]:
    """Curated base lexicon plus the student's own weak-topic names.

    The base is always included; the student's weak topics (e.g. "Rotational
    Motion", "Organic Chemistry") are appended so the keyterm list visibly tracks
    what this student studies. Result is deduplicated (order-preserving) and
    capped to a safe keyterm count.
    """
    terms = all_terms()
    terms.extend(profile.get("weak_topics", []))

    seen: set[str] = set()
    out: list[str] = []
    for term in terms:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            out.append(term)
    return out[:_KEYTERM_CAP]
