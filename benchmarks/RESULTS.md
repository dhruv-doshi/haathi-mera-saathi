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

## Layer 1 — keyterm boosting (real audio, 12 phrases, 14 terms)

text → Cartesia sonic-2 → WAV → Deepgram nova-3 (keyterm OFF vs ON).

| Pipeline | Term recovery |
|---|---|
| V1 (no keyterm) | 57% (8/14) |
| V1.5 Layer 1 (keyterm) | 64% (9/14) |
| V1.5 full (keyterm + normalizer) | 64% (9/14) |

**Do not trust this +7 at face value — two confounds dominate:**

1. **Scoring artifact (Devanagari).** Deepgram with `language=multi` often returns
   correct *Hindi-script* transcripts that my Latin-substring metric scores as misses:
   - `lambit karan` → `लंबित कारण` (correct! scored 0/2)
   - `visthapan` → `वे स्थापन` (≈correct, scored 0/1)
   - `samakalan` → `समकलन` (correct, scored 0); keyterm just flipped it to Latin `Samakalan` (scored 1).
   So the only "+1" is a **script flip, not an error fix**.

2. **TTS audio is too clean.** A single synthetic voice with clean pronunciation
   barely produces mishearings — only **2 of 12** phrases had genuine errors:
   - `avkalan` → `अब कलम` ("now pen"); keyterm made it `अब polynomial` — **keyterm
     hallucinated a boosted term.**
   - `tvaran` → `तुरंत` ("immediately"); keyterm → **empty string** — keyterm suppressed it.

   Layer 1 fixed **neither** genuine error and **regressed both**. That's a real
   finding: aggressive keyterm lists can inject wrong terms or drop unlisted ones.

### Honest verdict

- **Layer 2 (normalizer) is the proven win** — +27 points where it applies, zero
  casual corruption. Caveats: gate misses total garbles; latency budget is tight.
- **Layer 1 (keyterms) is unproven and shows regression risk** on this set. The
  synthetic-audio benchmark is **not valid enough** to judge it — clean TTS doesn't
  reproduce real student speech, and Devanagari breaks the metric.

### What this benchmark still needs (to be trustworthy)
1. **Real human recordings** of code-mixed academic speech (accents, noise, real
   mispronunciation) — the only way to measure the true mishearing rate and the
   real keyterm effect. Drop them into `benchmarks/audio/` and re-run.
2. **Transliteration-aware scoring** so correct Devanagari counts as correct.
3. **Keyterm regression check** — investigate the `avkalan→polynomial` hallucination
   and `tvaran→∅` drop; consider a smaller / higher-precision keyterm list.
