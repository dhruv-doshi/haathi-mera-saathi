"""Keyterm investigation + larger synthetic set.

Goal: is Deepgram nova-3 keyterm prompting actually helping, and does the
40-term list cause the regressions seen earlier (avkalan->polynomial, tvaran
dropped)? Compare three configs on the same audio:
  OFF    : no keyterms (V1)
  SMALL  : ~15 high-value, mishearing-prone terms (excludes easy English words)
  FULL   : 40 terms (current production default)

Fixes the earlier scoring artifact: each concept is matched against BOTH Latin
and Devanagari surface forms, so correct Hindi-script output counts as correct.

Validity caveats (still synthetic): all available Cartesia voices are English,
and TTS pronunciation is clean — this under-produces real mishearings. Treat as
a controlled regression signal, not a real-world rate. WAVs saved to
benchmarks/audio/synth/.

Run:  .venv/bin/python benchmarks/benchmark_keyterm.py
"""

import json
import os
import sys
import wave
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env.local")

import config  # noqa: E402
import lexicon  # noqa: E402

OUT = ROOT / "benchmarks" / "audio" / "synth"
OUT.mkdir(parents=True, exist_ok=True)
CARTESIA_KEY = os.environ["CARTESIA_API_KEY"]
DEEPGRAM_KEY = os.environ["DEEPGRAM_API_KEY"]
RATE = 16000

# Concept -> accepted surface forms (Latin + Devanagari). Recovery = any present.
CONCEPTS = {
    "sin": ["sin", "साइन", "सिन"],
    "cos": ["cos", "कॉस", "कोस"],
    "tan": ["tan", "टैन", "टान"],
    "cosec": ["cosec", "cosecant", "कोसेक"],
    "theta": ["theta", "थीटा", "थेटा"],
    "avkalan": ["avkalan", "अवकलन"],
    "samakalan": ["samakalan", "समाकलन", "समकलन"],
    "derivative": ["derivative", "अवकलज"],
    "integration": ["integration", "समाकलन"],
    "tvaran": ["tvaran", "त्वरण"],
    "veg": ["veg", "वेग"],
    "visthapan": ["visthapan", "विस्थापन"],
    "lambit_karan": ["lambit karan", "लंबित कारण", "लम्बित कारण"],
    "torque": ["torque", "टॉर्क"],
    "momentum": ["momentum", "संवेग"],
    "electrophile": ["electrophile", "इलेक्ट्रोफाइल"],
    "nucleophile": ["nucleophil", "न्यूक्लियोफ"],
    "quadratic": ["quadratic", "द्विघात"],
    "polynomial": ["polynomial", "बहुपद"],
    "logarithm": ["logarithm", "लघुगणक"],
}

# High-value SMALL list: mishearing-prone terms only. Deliberately EXCLUDES easy
# English words Deepgram already nails (polynomial, quadratic, momentum...) — those
# are the suspected hallucination source.
SMALL = [
    "sin", "cos", "tan", "cosec", "theta", "avkalan", "samakalan", "derivative",
    "tvaran", "veg", "visthapan", "lambit karan", "torque", "electrophile", "nucleophile",
]

# id, text, [concept keys present as ground truth]
PHRASES = [
    ("p01", "sin theta ka value kya hai", ["sin", "theta"]),
    ("p02", "cos theta plus sin theta nikalo", ["cos", "sin", "theta"]),
    ("p03", "cosec x ki value kya hogi", ["cosec"]),
    ("p04", "tan theta equals one solve karo", ["tan", "theta"]),
    ("p05", "sin squared plus cos squared kitna hota hai", ["sin", "cos"]),
    ("p06", "avkalan kaise karte hain is function ka", ["avkalan"]),
    ("p07", "samakalan nikalna hai mujhe", ["samakalan"]),
    ("p08", "derivative of x squared kya hoga", ["derivative"]),
    ("p09", "integration by parts samjhao", ["integration"]),
    ("p10", "is question mein avkalan use karna padega", ["avkalan"]),
    ("p11", "tvaran nikalo is body ka", ["tvaran"]),
    ("p12", "veg aur tvaran mein kya difference hai", ["veg", "tvaran"]),
    ("p13", "visthapan kitna hua total", ["visthapan"]),
    ("p14", "lambit karan kya hota hai", ["lambit_karan"]),
    ("p15", "torque on the rod kitna hai", ["torque"]),
    ("p16", "momentum conserve hota hai yahan", ["momentum"]),
    ("p17", "electrophile kya hota hai samjhao", ["electrophile"]),
    ("p18", "nucleophile attack kaise karta hai", ["nucleophile"]),
    ("p19", "quadratic equation solve karna hai", ["quadratic"]),
    ("p20", "polynomial ka degree kya hai", ["polynomial"]),
    ("p21", "logarithm of hundred kitna hota hai", ["logarithm"]),
    ("p22", "sir sin theta thirty degree pe kya hai", ["sin", "theta"]),
    ("p23", "cos theta ka graph kaise banta hai", ["cos", "theta"]),
    ("p24", "tvaran ka formula bhul gaya hoon", ["tvaran"]),
    ("p25", "avkalan aur samakalan dono confuse hote hain", ["avkalan", "samakalan"]),
    ("p26", "lambit karan wala concept clear nahi hai", ["lambit_karan"]),
    ("p27", "veg constant hai toh tvaran zero hoga", ["veg", "tvaran"]),
    ("p28", "derivative aur avkalan same cheez hai kya", ["derivative", "avkalan"]),
    ("p29", "cosec aur sec ka difference batao", ["cosec"]),
    ("p30", "electrophile aur nucleophile mein confusion hai", ["electrophile", "nucleophile"]),
    ("p31", "sin theta by cos theta tan hota hai", ["sin", "cos", "tan", "theta"]),
    ("p32", "visthapan vector quantity hai kya", ["visthapan"]),
    ("p33", "torque kaise calculate karte hain", ["torque"]),
    ("p34", "momentum ka conservation samjhao", ["momentum"]),
    ("p35", "integration ka basic rule kya hai", ["integration"]),
    ("p36", "samakalan ki limit kaise lagate hain", ["samakalan"]),
    ("p37", "tan inverse theta kya hota hai", ["tan", "theta"]),
    ("p38", "avkalan se slope nikalte hain", ["avkalan"]),
    ("p39", "tvaran due to gravity kitna hota hai", ["tvaran"]),
    ("p40", "lambit karan aur samaantar mein fark", ["lambit_karan"]),
    ("p41", "polynomial ko factor kaise karein", ["polynomial"]),
    ("p42", "logarithm rules yaad nahi hain", ["logarithm"]),
    ("p43", "sin theta ka maximum value one hota hai", ["sin", "theta"]),
    ("p44", "veg kaise badalta hai time ke saath", ["veg"]),
    ("p45", "derivative chain rule se karte hain", ["derivative"]),
    ("p46", "cosec theta undefined kab hota hai", ["cosec", "theta"]),
    ("p47", "electrophile addition reaction samjhao", ["electrophile"]),
    ("p48", "quadratic formula yaad karna hai", ["quadratic"]),
]


def voices():
    r = requests.get("https://api.cartesia.ai/voices",
                     headers={"X-API-Key": CARTESIA_KEY, "Cartesia-Version": "2025-04-16"},
                     timeout=30)
    r.raise_for_status()
    data = r.json()
    items = data if isinstance(data, list) else data.get("data", [])
    return [v["id"] for v in items] or [config.TTS_VOICE]


def synth(text, path, voice_id, speed):
    body = {
        "model_id": "sonic-2",
        "transcript": text,
        "voice": {"mode": "id", "id": voice_id, "__experimental_controls": {"speed": speed}},
        "output_format": {"container": "raw", "encoding": "pcm_s16le", "sample_rate": RATE},
        "language": "en",
    }
    r = requests.post("https://api.cartesia.ai/tts/bytes",
                      headers={"X-API-Key": CARTESIA_KEY, "Cartesia-Version": "2024-11-13",
                               "Content-Type": "application/json"},
                      json=body, timeout=60)
    if r.status_code >= 400:  # speed control unsupported -> retry plain
        body["voice"].pop("__experimental_controls", None)
        r = requests.post("https://api.cartesia.ai/tts/bytes",
                          headers={"X-API-Key": CARTESIA_KEY, "Cartesia-Version": "2025-04-16",
                                   "Content-Type": "application/json"},
                          json=body, timeout=60)
    r.raise_for_status()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(r.content)


def transcribe(path, keyterms):
    params = {"model": "nova-3", "language": "multi", "punctuate": "true"}
    if keyterms:
        params["keyterm"] = keyterms
    r = requests.post("https://api.deepgram.com/v1/listen",
                      headers={"Authorization": f"Token {DEEPGRAM_KEY}", "Content-Type": "audio/wav"},
                      params=params, data=path.read_bytes(), timeout=60)
    r.raise_for_status()
    alts = r.json()["results"]["channels"][0]["alternatives"]
    return alts[0]["transcript"] if alts else ""


def has(concept, text):
    low = text.lower()
    return any(form.lower() in low for form in CONCEPTS[concept])


def main():
    vlist = voices()
    speeds = ["slow", "normal", "fast"]
    configs = {"OFF": None, "SMALL": SMALL, "FULL": lexicon.all_terms()[:40]}

    scores = {c: 0 for c in configs}
    regressions = {c: [] for c in configs if c != "OFF"}
    total = 0
    rows = []
    manifest = {}

    for i, (pid, text, concepts) in enumerate(PHRASES):
        voice = vlist[i % len(vlist)]
        speed = speeds[i % len(speeds)]
        wav = OUT / f"{pid}.wav"
        synth(text, wav, voice, speed)
        manifest[pid] = {"text": text, "concepts": concepts, "voice": voice, "speed": speed}

        trans = {c: transcribe(wav, kt) for c, kt in configs.items()}
        per = {}
        for c in configs:
            per[c] = {con: has(con, trans[c]) for con in concepts}
            scores[c] += sum(per[c].values())
        for c in regressions:
            for con in concepts:
                if per["OFF"][con] and not per[c][con]:
                    regressions[c].append((pid, con, trans["OFF"], trans[c]))
        total += len(concepts)
        rows.append({"id": pid, "text": text, "concepts": concepts,
                     "voice": voice, "speed": speed, "trans": trans})
        print(f"[{pid}] {text!r}")
        for c in configs:
            hit = sum(per[c].values())
            print(f"   {c:6}: {trans[c]!r}  {hit}/{len(concepts)}")
        print()

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    (ROOT / "benchmarks" / "results_keyterm.json").write_text(
        json.dumps({"total": total, "scores": scores,
                    "regressions": {c: [list(x) for x in r] for c, r in regressions.items()},
                    "rows": rows}, indent=2, ensure_ascii=False))

    print("=" * 60)
    print(f"Phrases: {len(PHRASES)}   ground-truth concepts: {total}")
    print(f"Voices used: {len(vlist)} (all English)   speeds: slow/normal/fast")
    print()
    print(f"{'Config':8} {'recovery':>10} {'regressions vs OFF':>20}")
    for c in configs:
        reg = "-" if c == "OFF" else str(len(regressions[c]))
        print(f"{c:8} {scores[c]/total*100:>9.0f}% {reg:>20}")
    print()
    for c in regressions:
        if regressions[c]:
            print(f"{c} regressions (concept lost vs OFF):")
            for pid, con, off, on in regressions[c]:
                print(f"  [{pid}] {con}: OFF={off!r}  ->  {c}={on!r}")
            print()
    print(f"Saved -> benchmarks/audio/synth/ ({len(PHRASES)} WAVs), results_keyterm.json")


if __name__ == "__main__":
    main()
