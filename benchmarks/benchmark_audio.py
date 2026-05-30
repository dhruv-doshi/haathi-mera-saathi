"""V1 vs V1.5 — Layer 1 (STT keyterm boosting) + full pipeline, on real audio.

Pipeline:
  text  --Cartesia sonic-2-->  WAV (saved)  --Deepgram nova-3-->  transcript

For each phrase it runs Deepgram three ways and scores term recovery vs the known
ground-truth terms:
  - V1            : nova-3, NO keyterms, NO normalizer  (today's pipeline)
  - V1.5 Layer 1  : nova-3 WITH keyterms                (prevention at source)
  - V1.5 full     : keyterms + normalizer               (prevention + correction)

VALIDITY CAVEAT: the audio here is TTS (one synthetic voice, clean pronunciation).
Real students mispronounce, have accents, and sit in noise — so this under-states
the real mishearing rate. Treat these numbers as a controlled, reproducible signal,
NOT a substitute for a human-recorded gold set. WAVs are saved to benchmarks/audio/
so they can be inspected or swapped for real recordings later.

Run:  .venv/bin/python benchmarks/benchmark_audio.py
"""

import asyncio
import json
import sys
import wave
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env.local")

import os  # noqa: E402

import config  # noqa: E402
import lexicon  # noqa: E402
import normalizer  # noqa: E402

AUDIO_DIR = ROOT / "benchmarks" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

CARTESIA_KEY = os.environ["CARTESIA_API_KEY"]
DEEPGRAM_KEY = os.environ["DEEPGRAM_API_KEY"]
SAMPLE_RATE = 16000

LEXICON = lexicon.all_terms()
# Deepgram keyterm via REST — cap the list to keep the request sane.
KEYTERMS = LEXICON[:40]

# id, spoken text (correct academic speech), ground-truth key terms
PHRASES = [
    ("trig_sin",     "sin theta ka value kya hai",                          ["sin"]),
    ("trig_cosec",   "cosec x ki value nikalo",                             ["cosec"]),
    ("trig_sincos",  "cos theta plus sin theta",                            ["cos", "sin"]),
    ("calc_avkalan", "avkalan kaise karte hain",                            ["avkalan"]),
    ("calc_samak",   "samakalan nikalna hai",                               ["samakalan"]),
    ("phys_lambit",  "lambit karan kya hota hai",                           ["lambit", "karan"]),
    ("phys_tvaran",  "tvaran nikalo is body ka",                            ["tvaran"]),
    ("phys_visth",   "visthapan kitna hua",                                 ["visthapan"]),
    ("phys_torque",  "torque on the rod kitna hai",                         ["torque"]),
    ("chem_ephile",  "electrophile kya hota hai",                           ["electrophile"]),
    ("chem_nphile",  "nucleophilic substitution samjhao",                   ["nucleophil"]),
    ("mixed_deg",    "sin theta ka value kya hota hai thirty degree pe",    ["sin"]),
]


def synth(text: str, path: Path) -> None:
    """Cartesia sonic-2 -> raw PCM -> saved WAV."""
    resp = requests.post(
        "https://api.cartesia.ai/tts/bytes",
        headers={
            "X-API-Key": CARTESIA_KEY,
            "Cartesia-Version": "2025-04-16",
            "Content-Type": "application/json",
        },
        json={
            "model_id": "sonic-2",
            "transcript": text,
            "voice": {"mode": "id", "id": config.TTS_VOICE},
            "output_format": {
                "container": "raw",
                "encoding": "pcm_s16le",
                "sample_rate": SAMPLE_RATE,
            },
            "language": "hi",
        },
        timeout=60,
    )
    resp.raise_for_status()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(resp.content)


def transcribe(path: Path, keyterms: list[str] | None) -> str:
    params = {"model": "nova-3", "language": "multi", "punctuate": "true"}
    if keyterms:
        params["keyterm"] = keyterms  # repeated query param
    resp = requests.post(
        "https://api.deepgram.com/v1/listen",
        headers={"Authorization": f"Token {DEEPGRAM_KEY}", "Content-Type": "audio/wav"},
        params=params,
        data=path.read_bytes(),
        timeout=60,
    )
    resp.raise_for_status()
    alts = resp.json()["results"]["channels"][0]["alternatives"]
    return alts[0]["transcript"] if alts else ""


def recov(text: str, keys: list[str]) -> int:
    low = text.lower()
    return sum(k.lower() in low for k in keys)


async def main():
    llm = config.build_normalizer_llm()
    rows = []
    tot = v1 = l1 = full = 0
    manifest = {}

    for pid, text, keys in PHRASES:
        wav = AUDIO_DIR / f"{pid}.wav"
        synth(text, wav)
        manifest[pid] = {"text": text, "keys": keys, "wav": wav.name}

        t_v1 = transcribe(wav, None)
        t_l1 = transcribe(wav, KEYTERMS)
        t_full = await normalizer.normalize(t_l1, LEXICON, llm, timeout=8.0) \
            if normalizer.looks_academic(t_l1, LEXICON) else t_l1

        n = len(keys)
        r_v1, r_l1, r_full = recov(t_v1, keys), recov(t_l1, keys), recov(t_full, keys)
        tot += n
        v1 += r_v1
        l1 += r_l1
        full += r_full
        rows.append({"id": pid, "text": text, "keys": keys, "n": n,
                     "v1_stt": t_v1, "l1_stt": t_l1, "full": t_full,
                     "r_v1": r_v1, "r_l1": r_l1, "r_full": r_full})
        print(f"[{pid}] truth: {text!r}")
        print(f"   V1 (no keyterm) : {t_v1!r}   {r_v1}/{n}")
        print(f"   V1.5 L1 (keyterm): {t_l1!r}   {r_l1}/{n}")
        print(f"   V1.5 full        : {t_full!r}   {r_full}/{n}")
        print()

    (AUDIO_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    (ROOT / "benchmarks" / "results_layer1.json").write_text(
        json.dumps({"total_terms": tot, "v1": v1, "l1": l1, "full": full, "rows": rows},
                   indent=2, ensure_ascii=False))

    print("=" * 60)
    print(f"Phrases: {len(PHRASES)}   ground-truth terms: {tot}")
    print(f"Term Recovery  V1 (no keyterm)   : {v1/tot*100:>3.0f}%  ({v1}/{tot})")
    print(f"Term Recovery  V1.5 Layer 1      : {l1/tot*100:>3.0f}%  ({l1}/{tot})")
    print(f"Term Recovery  V1.5 full pipeline: {full/tot*100:>3.0f}%  ({full}/{tot})")
    print(f"\nWAVs saved -> {AUDIO_DIR.relative_to(ROOT)}/  (+ manifest.json)")


if __name__ == "__main__":
    asyncio.run(main())
