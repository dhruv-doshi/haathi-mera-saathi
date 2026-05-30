"""Dedicated transcript-normalization stage — the PRD 6.7 node.

Sits between STT and the mentor LLM. Two pieces:
- looks_academic(text, lexicon): a cheap, LLM-free gate. Only academic-looking
  transcripts are worth correcting; everything else passes through untouched, so
  casual turns ("haan theek hai") add zero latency.
- normalize(text, lexicon, llm, timeout): a single fast-model pass that fixes
  misheard math/science terms in code-mixed Hindi/English speech, preserving
  everything else verbatim. Timeout-guarded; never raises into the voice loop.
"""

import asyncio
import logging
import re

from livekit.agents import llm as _llm

logger = logging.getLogger("normalizer")

# Default safety cap, overridable per call. This is NOT a tight budget — a remote
# Haiku round-trip realistically takes a few hundred ms — it is the point past
# which we give up and use the raw transcript so the voice turn stays responsive.
_DEFAULT_TIMEOUT_S = 1.5

# Tokens that strongly signal math/science speech (common mishearings included).
# Deliberately small and fast — this is a gate, not a classifier.
_MATH_TOKENS = re.compile(
    r"\b(sin|sine|signs|cos|kos|cosine|tan|cosec|co\s?sec|sec|cot|theta|log|"
    r"integration|integral|derivative|differentiat\w*|limit|degree|degrees|"
    r"square|squared|root|equation)\b",
    re.IGNORECASE,
)

_SYSTEM = (
    "You correct raw speech-to-text from an Indian academic voice tutor. The "
    "student speaks code-mixed Hindi and English about math and science. Fix ONLY "
    "misheard math/science terms (for example 'signs' or 'sine' meaning the sine "
    "function, 'co sec' meaning 'cosec', 'kos theta' meaning 'cos theta'). Hindi "
    "technical words like 'lambit karan' (perpendicular) or 'tvaran' (acceleration) "
    "are correct as-is — keep them. Preserve the student's exact language mix and "
    "every non-academic word verbatim. Make minimal edits. If you are unsure, leave "
    "the text unchanged. Output ONLY the corrected transcript — no quotes, labels, "
    "or commentary."
)


def looks_academic(text: str, lexicon: list[str]) -> bool:
    """True if the transcript is worth sending to the normalizer."""
    if not text or not text.strip():
        return False
    low = text.lower()
    if _MATH_TOKENS.search(low):
        return True
    if any(ch.isdigit() for ch in low):
        return True
    return any(term.lower() in low for term in lexicon)


async def normalize(
    text: str,
    lexicon: list[str],
    llm,
    timeout: float = _DEFAULT_TIMEOUT_S,
) -> str:
    """Return a corrected transcript, or the original on any failure/timeout."""
    try:
        ctx = _llm.ChatContext.empty()
        reference = ", ".join(lexicon[:60])
        ctx.add_message(role="system", content=f"{_SYSTEM}\n\nKnown terms: {reference}")
        ctx.add_message(role="user", content=text)

        resp = await asyncio.wait_for(llm.chat(chat_ctx=ctx).collect(), timeout=timeout)
        corrected = (resp.text or "").strip()
        if not corrected:
            return text
        if corrected != text:
            logger.info("normalized: %r -> %r", text, corrected)
        return corrected
    except asyncio.TimeoutError:
        logger.warning("normalizer timed out (%.0fms); using raw transcript", timeout * 1000)
        return text
    except Exception:
        logger.exception("normalizer failed; using raw transcript")
        return text
