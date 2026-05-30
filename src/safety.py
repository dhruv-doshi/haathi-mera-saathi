"""Deterministic safety layer — distress detection independent of the LLM.

The mentor serves minors and may receive disclosures of self-harm, abuse, or
serious hopelessness. The system prompt asks the LLM to escalate, but that is
not a guarantee — a model can miss it, paraphrase it away, or be talked past.
This module is a CODE-level backstop:

- detect_distress(text): a cheap, LLM-free check over the user's transcript,
  returning a category ("self_harm" | "abuse" | "distress") or None.
- helpline_line(language_pref): a fixed, supportive line that ALWAYS contains
  the Tele-MANAS helpline number 14416, spoken verbatim via TTS — so the number
  can never be dropped or refused by the model.
- ESCALATION_DIRECTIVE: high-priority guidance injected into subsequent LLM
  turns so the conversation that wraps the fixed line stays calm and present.

Posture: favor RECALL. A missed disclosure is far costlier than a false alarm,
and because the triggered response is warm and non-alarming (a kind check-in
plus an offer of help), an over-trigger degrades gracefully. To avoid the worst
false positives, ambiguous short words are only matched with a self-referential
phrase (e.g. "cut myself", never bare "cut"; "feel hopeless", never "hopeless"),
so academic/idiomatic uses ("cut-off", "this chapter is killing me", "dead
tired", "marks kaat liye") do NOT trigger.

The Tele-MANAS number (14416) is the Government of India national 24x7 toll-free
mental health helpline (verified 2026-05).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Curated, auditable distress phrases (lowercase). Multi-word / self-referential
# by design so they read clearly and resist false positives. Covers English,
# Hinglish, and transliterated Hindi. Edit these lists to tune coverage.
# ---------------------------------------------------------------------------

SELF_HARM_PHRASES = [
    # English
    "kill myself", "killing myself", "end my life", "ending my life",
    "take my life", "want to die", "wanna die", "i want to die",
    "don't want to live", "do not want to live", "dont want to live",
    "no reason to live", "no point in living", "no point living",
    "hurt myself", "harm myself", "cut myself", "cutting myself", "suicid",
    # Hinglish / Hindi (transliterated)
    "marna chahta", "marna chahti", "mar jaana chahta", "mar jana chahta",
    "mar jaana chahti", "jeena nahi chahta", "jeena nahi chahti",
    "jeene ka mann nahi", "marne ka mann", "khud ko khatam",
    "apne aap ko khatam", "zinda nahi rehna", "zinda nahi rahna",
    "khudkushi", "atmahatya", "khudkhushi",
]

ABUSE_PHRASES = [
    # English
    "hits me", "hitting me", "beats me", "beating me", "abuses me",
    "abusing me", "touched me", "touches me", "molest",
    # Hinglish / Hindi
    "mujhe maarte hain", "mujhe marte hain", "ghar mein maarte",
    "mujhe peette hain", "ghar mein peette", "galat tarike se chua",
    "galat tarike se chhua",
]

DISTRESS_PHRASES = [
    # Serious hopelessness — NOT ordinary study frustration (that's the LLM's
    # personal_support mode). Kept self-referential to avoid "this is hopeless".
    "feel hopeless", "feeling hopeless", "i'm hopeless", "feel worthless",
    "feeling worthless", "i am worthless", "i'm worthless",
    "can't go on", "cannot go on", "cant go on",
    "can't take it anymore", "cant take it anymore",
    "better off dead", "better off without me", "no way out",
    "give up on life", "everything is pointless", "life is pointless",
    # Hinglish / Hindi
    "ab aur nahi", "bardaasht nahi hota", "bardasht nahi hota",
    "koi raasta nahi bacha", "sab kuch khatam ho gaya",
]

# Ordered so the most acute category wins when several match.
_CATEGORIES = [
    ("self_harm", SELF_HARM_PHRASES),
    ("abuse", ABUSE_PHRASES),
    ("distress", DISTRESS_PHRASES),
]


def detect_distress(text: str) -> str | None:
    """Return a distress category if the transcript matches, else None.

    Deterministic and LLM-free: normalizes whitespace/case, then checks the
    curated phrase lists. Safe to call on every final transcript.
    """
    if not text or not text.strip():
        return None
    low = " ".join(text.lower().split())
    for category, phrases in _CATEGORIES:
        if any(phrase in low for phrase in phrases):
            return category
    return None


# ---------------------------------------------------------------------------
# Fixed, supportive responses. Spoken verbatim via TTS — never LLM-generated —
# so the helpline number is guaranteed to be heard. The number is given as
# digits AND spelled out for voice clarity.
# ---------------------------------------------------------------------------

_HELPLINE_HI = (
    "Ek minute ruk. Main yahin hoon tumhare saath, aur tum bilkul akele nahi ho. "
    "Jo tum mehsoos kar rahe ho wo important hai. Please abhi kisi bharose wale "
    "insaan se baat karo — koi parent, teacher, ya close dost. Aur ek free "
    "helpline hai jo chaubees ghante hai, Tele-MANAS — number hai 14416, yaani "
    "one, four, four, one, six. Main yahin hoon, kahin nahi jaa raha."
)

_HELPLINE_EN = (
    "Hey, let's pause for a second. I'm right here with you, and you are not alone. "
    "What you're feeling matters. Please reach out right now to someone you trust — "
    "a parent, a teacher, or a close friend. And there's a free helpline open "
    "around the clock, Tele-MANAS — the number is 14416, that's one, four, four, "
    "one, six. I'm staying right here with you."
)


def helpline_line(language_pref: str = "Hinglish") -> str:
    """A fixed, warm support line that always contains the helpline number."""
    pref = (language_pref or "").strip().lower()
    if pref in ("english", "en"):
        return _HELPLINE_EN
    return _HELPLINE_HI


# Injected as a high-priority system message on subsequent turns once escalated,
# so the model's wrap-around conversation stays in a safe register.
ESCALATION_DIRECTIVE = (
    "[SAFETY OVERRIDE — ACTIVE] The student has expressed something serious "
    "(distress, self-harm, or abuse). Stop all academics and all banter "
    "immediately. Be calm, warm, and fully present; take them completely "
    "seriously and do not minimise it. Do not diagnose or act as a therapist. "
    "Gently encourage them to reach out right now to a trusted person (parent, "
    "teacher, relative, close friend) and remind them the free Tele-MANAS "
    "helpline 14416 is available 24x7. Stay with them. Keep everything "
    "age-appropriate. Only return to studies if the student is clearly safe and "
    "asks to."
)
