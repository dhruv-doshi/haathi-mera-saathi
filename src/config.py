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

# --- Language behavior: Hindi / Hinglish / English (code-mixed) ---
# Deepgram "multi" enables code-mixed Indian-language transcription.
STT_LANGUAGE = "multi"

# --- Memory backend: "local" (default, no credits) or "synap" ---
MEMORY_BACKEND = "local"


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


def build_stt():
    if STT_PROVIDER == "deepgram":
        from livekit.plugins import deepgram

        return deepgram.STT(model=STT_MODEL, language=STT_LANGUAGE)
    if STT_PROVIDER == "openai":
        from livekit.plugins import openai

        return openai.STT(model=STT_MODEL)
    raise ValueError(f"Unsupported STT_PROVIDER: {STT_PROVIDER}")


def build_tts():
    if TTS_PROVIDER == "cartesia":
        from livekit.plugins import cartesia

        return cartesia.TTS(model=TTS_MODEL)
    if TTS_PROVIDER == "openai":
        from livekit.plugins import openai

        return openai.TTS(model=TTS_MODEL)
    raise ValueError(f"Unsupported TTS_PROVIDER: {TTS_PROVIDER}")
