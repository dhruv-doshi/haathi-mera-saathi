"""Central configuration: provider + model selection for the voice pipeline.

This is the single place that loads env vars and decides which LLM / STT / TTS
provider and model the agent uses. Pipeline code never hardcodes keys or model
names — it calls the build_* factories below.

To switch a provider, change one *_PROVIDER line. To switch a model, change one
*_MODEL line. API keys are read from .env.local by the plugins themselves.
"""

from dotenv import load_dotenv

load_dotenv(".env.local")

# --- Provider selection (change one line to switch provider) ---
LLM_PROVIDER = "openrouter"   # "openai" or "openrouter"
STT_PROVIDER = "deepgram"
TTS_PROVIDER = "cartesia"

# --- Model selection (change one line to switch model) ---
# OpenRouter model names: "anthropic/claude-sonnet-4-5", "google/gemini-2.0-flash-001", etc.
# OpenAI model names:     "gpt-4o-mini", "gpt-4o"
LLM_MODEL = "anthropic/claude-sonnet-4-5"
STT_MODEL = "nova-3"
TTS_MODEL = "sonic-2"
TTS_VOICE = "910fb75e-1d20-4840-ac63-ac6b26a71bdc"

# --- Language behavior: Hindi / Hinglish / English (code-mixed) ---
# Deepgram "multi" enables code-mixed Indian-language transcription.
STT_LANGUAGE = "multi"

# --- Academic-term normalizer (V1.5, PRD 6.7) ---
# A fast model corrects misheard math/science terms between STT and the mentor
# LLM, but only on academic-looking or low-confidence transcripts.
NORMALIZER_ENABLED = True
NORMALIZER_MODEL = "anthropic/claude-haiku-4-5"
CONFIDENCE_THRESHOLD = 0.6   # final transcripts below this are sent to normalize
NORMALIZER_TIMEOUT_S = 1.5   # safety cap; falls back to raw transcript past this

# --- Memory backend: "local" (default, no credits) or "synap" ---
MEMORY_BACKEND = "local"
# How many past sessions are recapped into the opening of the next call.
MEMORY_RECENT_N = 3

# --- Learnings extraction (self-updating profile) ---
# At session end a fast model reads the transcript and extracts durable learnings
# (new weak/strong topics, scores, commitments) into the memory `learned` block,
# which is merged with the static profile seed on the next call. Bounded by a
# timeout; degrades to a heuristic summary on any failure so shutdown never blocks.
LEARNINGS_ENABLED = True
LEARNINGS_MODEL = "anthropic/claude-haiku-4-5"
LEARNINGS_TIMEOUT_S = 5.0   # looser than the voice budget — no one is waiting

# --- Deterministic safety layer ---
# Code-level distress detection on the user transcript, independent of the LLM.
# On trigger it forces escalation and speaks the Tele-MANAS helpline via TTS.
SAFETY_ENABLED = True


def build_llm():
    if LLM_PROVIDER == "openai":
        from livekit.plugins import openai

        return openai.LLM(model=LLM_MODEL)
    if LLM_PROVIDER == "openrouter":
        import os
        from livekit.plugins import openai

        return openai.LLM(
            model=LLM_MODEL,
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
    raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")


def build_stt(keyterms: list[str] | None = None):
    if STT_PROVIDER == "deepgram":
        from livekit.plugins import deepgram

        kwargs = {"model": STT_MODEL, "language": STT_LANGUAGE}
        if keyterms:
            # nova-3 keyterm prompting (NOT `keywords`, which is nova-2 only).
            kwargs["keyterm"] = keyterms
        return deepgram.STT(**kwargs)
    if STT_PROVIDER == "openai":
        from livekit.plugins import openai

        return openai.STT(model=STT_MODEL)
    raise ValueError(f"Unsupported STT_PROVIDER: {STT_PROVIDER}")


def build_normalizer_llm():
    """Fast, cheap model for the transcript-normalization stage (PRD 6.7)."""
    if LLM_PROVIDER == "openai":
        from livekit.plugins import openai

        return openai.LLM(model=NORMALIZER_MODEL)
    if LLM_PROVIDER == "openrouter":
        import os
        from livekit.plugins import openai

        return openai.LLM(
            model=NORMALIZER_MODEL,
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
    raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")


def build_learnings_llm():
    """Fast, cheap model for the end-of-session learnings extraction."""
    if LLM_PROVIDER == "openai":
        from livekit.plugins import openai

        return openai.LLM(model=LEARNINGS_MODEL)
    if LLM_PROVIDER == "openrouter":
        import os
        from livekit.plugins import openai

        return openai.LLM(
            model=LEARNINGS_MODEL,
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
    raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")


def build_tts():
    if TTS_PROVIDER == "cartesia":
        from livekit.plugins import cartesia

        return cartesia.TTS(model=TTS_MODEL, voice=TTS_VOICE)
    if TTS_PROVIDER == "openai":
        from livekit.plugins import openai

        return openai.TTS(model=TTS_MODEL)
    raise ValueError(f"Unsupported TTS_PROVIDER: {TTS_PROVIDER}")
