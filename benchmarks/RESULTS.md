# V1 vs V1.5 — Benchmark Results

Two layers, two benchmarks. Run them with:
```
.venv/bin/python benchmarks/benchmark_normalizer.py   # Layer 2 (text)
.venv/bin/python benchmarks/benchmark_audio.py        # Layer 1 (audio, saves WAVs)
```
Audio samples live in `benchmarks/audio/` (12 WAVs + `manifest.json`).

---

## Layer 2 — the normalizer (text-level, 36 phrases, 41 key terms)

Measures the transcript the brain *receives*: V1 sends raw STT text to the LLM;
V1.5 repairs it first. Mishearings here are plausible Deepgram errors I authored.

| Category | V1 recovery | V1.5 recovery |
|---|---|---|
| trig | 27% | **91%** |
| calc | 57% | 57% |
| phys | 33% | **56%** |
| chem | 50% | 50% |
| alg | 100% | 100% |
| mixed | 20% | **60%** |
| **Overall** | **41%** | **68%** |

- **Term recovery 41% → 68% (+27 points)** — clear, real win on Latin-script mishearings.
- **Over-correction on casual speech: 0/10.** Gate skips chit-chat; never corrupts it.
- **Gate recall 67%** — the gate MISSES fully-garbled terms (e.g. "aukalan", "electro file")
  because the correct token isn't present to trigger on. In production this is
  partly covered by the low-confidence trigger (Deepgram flags garbles) and by
  Layer 1 keyterms — neither of which this text-only test can see, so it *under-states*
  V1.5 here.
- **Latency: mean 1249ms, p50 983ms, p95 2553ms. Only 75% finish within the 1.5s
  production budget** → ~25% of corrections would time out and fall back to raw text.
  The OpenRouter→Haiku hop is the cost. Worth tuning (raise budget, or a faster path).

## Layer 1 — keyterm boosting (real audio)

text → Cartesia sonic-2 → WAV → Deepgram nova-3 (keyterm OFF / SMALL / FULL).

### First pass (12 phrases, Latin-only scoring) — MISLEADING, superseded
Showed 57%→64% and two apparent regressions (`avkalan→polynomial`, `tvaran→∅`).
Both were artifacts: a 12-clip set, one voice, and a Latin-substring metric that
scored correct Devanagari (`लंबित कारण`, `समकलन`) as misses. See the proper run below.

### Proper run (48 phrases, 10 voices, 3 speeds, Devanagari-aware scoring)
`benchmark_keyterm.py` — each concept matched against Latin **and** Hindi-script forms.

| Config | Term recovery | Regressions vs OFF |
|---|---|---|
| OFF (V1, no keyterm) | 53% (35/66) | — |
| SMALL (15 high-value terms) | 88% (58/66) | 1 (momentum, not in list) |
| FULL (40 terms, production default) | **89% (59/66)** | **0** |

- **Keyterm boosting is a big, real win: 53% → 89% (+36 points), zero regressions.**
- The earlier "regressions" **did not reproduce** — keyterm actually *fixes* them at scale:
  - `avkalan`: OFF `"Aufkalin"` → keyterm `"Avkalan"` ✓
  - `tvaran`: OFF `"Tuaren"` / `"ट्वार्न"` → keyterm `"tvaran"` ✓
  - `samakalan`: OFF `"Samakaland"` → keyterm `"Samakalan"` ✓
- **SMALL (15) ≈ FULL (40)**: 88% vs 89%. The smaller list captures almost all the
  benefit; on the English voices FULL edged it out with no regressions.
- Residual hard cases keyterm does NOT save: total garbles (`tvaran nikalo` → `"Tornicalo"`)
  and a rare drop (`quadratic` → `""`). Real but infrequent.

### Re-run on the PRODUCTION app voice (48 phrases, voice `910fb75e…`, language=hi)
The English voices above read romanized Hindi with an English accent. This run uses
the app's actual configured voice with `language=hi` — the most production-relevant set.

| Config | Term recovery | Regressions vs OFF |
|---|---|---|
| OFF (V1) | 62% (41/66) | — |
| **SMALL (15)** | **82% (54/66)** | **0** |
| FULL (40, current default) | 82% (54/66) | **2** |

- **Keyterm still a clear win: 62% → 82% (+20 points)** on the real app voice.
- **But FULL now regresses, and it is REPRODUCIBLE (3/3 trials):** the 40-term list makes
  Deepgram return an **empty transcript** for two `lambit karan …` sentences, which OFF
  and SMALL transcribe perfectly:
  - `lambit karan wala concept clear nahi hai` → FULL `""`, SMALL/OFF `लंबित कारण वाला…` ✓
  - `lambit karan aur samaantar mein fark` → FULL `""`, SMALL/OFF `लंबित कारण और…` ✓
  - (the shorter `lambit karan kya hota hai` is fine under FULL — length/list-size interaction)
- **SMALL matches FULL's recovery with ZERO regressions.** A long keyterm list can suppress
  whole utterances; a tight high-value list does not.
- **This contradicts the English-voice conclusion** — keyterm-list tuning is voice-dependent,
  and on the voice that actually ships, **smaller is safer**.

> ⚠️ Production note: `lexicon.build_keyterms` currently sends ~49 terms (all_terms + weak
> topics, cap 100) — even larger than the FULL(40) tested here, so the empty-drop risk
> applies to production. Recommend trimming to a high-value core (~15-20).

## Verdict

| Layer | Result | Confidence |
|---|---|---|
| **Layer 1 — keyterm** | **+20 pts** on app voice (62%→82%); +36 on English voices | Validated; tuning is voice-dependent |
| **Layer 2 — normalizer** | **+27 pts** text recovery, 0 casual corruption | Validated on text |

Both layers earn their place. **Action item:** on the production app voice, the large
keyterm list (~49 in `lexicon.py`) reproducibly drops whole `lambit karan` utterances to
empty; a 15-term high-value list matches recovery with **zero** regressions. **Trim the
production keyterm list.** Other open follow-ups: the normalizer's tight latency budget
(~25% exceed 1.5s) and gate recall on total garbles.

### Validity caveat (still true)
All audio is synthetic: clean TTS, and **all 10 Cartesia voices are English** (they read
romanized Hindi with an English accent). This under-produces real mishearings and accent
variation. The numbers are a strong controlled signal, not a real-world rate — a
human-recorded gold set (drop WAVs in `benchmarks/audio/`, re-run) remains the gold standard.
