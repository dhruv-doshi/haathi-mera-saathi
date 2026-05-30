# 🐘 Haathi Mera Saathi

A multilingual, voice-first academic mentor for Indian students (Class 6–12, Boards / JEE / NEET).

Not a chatbot. The warm senior in your hostel you call at 10 PM — the one who knows your weak chapters, remembers your last mock score, tells you what to drop with 15 days left, and is just as likely to run a breathing reset with you as explain SN1 vs SN2.

---

## What it does

- **Knows you** — student profile and prior session memory injected into every conversation
- **Gives direction, not just answers** — teaches, plans, strategizes, motivates, and steadies
- **Feels human** — Hinglish banter, mood-aware humour, guided breathing, dance breaks
- **Voice-first** — speak naturally, interrupt mid-sentence, switch topics freely
- **Multilingual** — Hindi, Hinglish, English, code-mixed mid-sentence
- **Hears the math** — code-mixed academic terms ("cos theta", "lambit karan", "avkalan") are recognized, not mangled ([V1.5](#academic-term-recognition-v15))

---

## Stack

| Layer | Choice |
|---|---|
| Voice orchestration | LiveKit Agents (Python) |
| STT | Deepgram `nova-3` (multilingual) + academic keyterm prompting |
| Transcript normalizer | Claude Haiku via OpenRouter (conditional academic-term repair) |
| LLM | Claude Sonnet via OpenRouter |
| TTS | Cartesia `sonic-2` |
| VAD + turn detection | Silero + LiveKit multilingual model |
| Web client | Vanilla HTML/JS + LiveKit JS SDK (CDN) |
| Memory | Local JSON (Maximem Synap stub included) |

---

## Project structure

```
haathi-mera-saathi/
├── src/
│   ├── agent.py          # LiveKit Agents pipeline — the brain (stt_node + llm_node)
│   ├── config.py         # Provider + model selection (one-line swaps)
│   ├── lexicon.py        # Academic keyterm lexicon (STT bias + normalizer context)
│   ├── normalizer.py     # Conditional transcript-normalization stage (PRD §6.7)
│   ├── prompt.py         # Mentor system prompt builder
│   ├── profile.py        # Student profile loader + formatter
│   ├── memory.py         # Session memory interface (local JSON / Synap)
│   ├── state.py          # Conversation state object + set_session_state tool
│   └── token_server.py   # LiveKit token endpoint + static file server
├── profiles/
│   └── aarav.json        # Sample student profile (Class 11, JEE)
├── memory/
│   └── aarav.json        # Prior session summary (written at session end)
├── web/
│   └── index.html        # Single-page browser client
├── benchmarks/           # V1 vs V1.5 benchmarks + saved audio samples + RESULTS.md
├── tests/                # Normalizer golden-set checks
├── demo/                 # Standalone presentation deck (open in a browser)
├── docs/                 # PRD and phase-by-phase build plan
└── requirements.txt
```

---

## Setup

**Prerequisites:** Python 3.11+, a LiveKit Cloud account, API keys for Deepgram, Cartesia, and OpenRouter.

```bash
# Clone and create virtualenv
git clone https://github.com/dhruv-doshi/haathi-mera-saathi.git
cd haathi-mera-saathi
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python src/agent.py download-files
```

Copy `.env.local` and fill in your keys:

```bash
cp .env.local.example .env.local   # or create manually
```

```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret

OPENROUTER_API_KEY=sk-or-...
DEEPGRAM_API_KEY=...
CARTESIA_API_KEY=sk_car_...
```

---

## Running

Two terminals:

**Terminal 1 — agent worker:**
```bash
.venv/bin/python src/agent.py dev
```

**Terminal 2 — web server:**
```bash
.venv/bin/python src/token_server.py
```

Open **http://localhost:8080**, click **Talk to Saathi**, allow mic access.

---

## Student profile

Edit `profiles/aarav.json` to change the demo student. The profile is injected into every session:

```json
{
  "name": "Aarav",
  "class": 11,
  "track": "JEE",
  "language_pref": "Hinglish",
  "weak_topics": ["Organic Chemistry", "Rotational Motion"],
  "strong_topics": ["Algebra"],
  "last_scores": [{"test": "Mock 4", "subject": "Physics", "score": "48/120"}],
  "syllabus_progress": {"Physics": "60%", "Chemistry": "40%"},
  "next_exam": {"name": "JEE Mains", "days_away": 15}
}
```

---

## Switching providers

All provider and model choices are in `src/config.py` — one line to change any of them:

```python
LLM_PROVIDER = "openrouter"        # or "openai"
LLM_MODEL    = "anthropic/claude-sonnet-4-5"

STT_PROVIDER = "deepgram"
STT_MODEL    = "nova-3"

TTS_PROVIDER = "cartesia"
TTS_MODEL    = "sonic-2"
TTS_VOICE    = "910fb75e-1d20-4840-ac63-ac6b26a71bdc"

# Academic-term normalizer (V1.5)
NORMALIZER_ENABLED   = True
NORMALIZER_MODEL     = "anthropic/claude-haiku-4-5"
CONFIDENCE_THRESHOLD = 0.6   # low-confidence finals are also normalized
NORMALIZER_TIMEOUT_S = 1.5   # falls back to raw transcript past this
```

---

## Academic-term recognition (V1.5)

Indian academic speech is wildly code-mixed — English "cos theta" next to Hindi "lambit karan" (perpendicular) in one breath — and `nova-3` mishears equation words ("sin x" → "signs", "avkalan" → "अब कलं"). V1.5 fixes this in **two dedicated layers** instead of a prompt patch:

1. **Prevent at the source** — `src/lexicon.py` seeds `nova-3`'s **keyterm prompting** with a curated academic lexicon (trig, calculus, Hindi physics, chemistry), auto-extended per student by their weak topics. Wired in `config.build_stt(keyterms=...)`.
2. **Correct what slips through** — `src/normalizer.py` is a dedicated normalization stage on LiveKit's `Agent.stt_node()` hook. A fast Haiku pass repairs the transcript **only** when it looks academic or STT confidence is low; casual turns pass through untouched (zero added latency). Timeout-guarded — never blocks the voice loop.

The old "hear the math" paragraph was removed from the mentor prompt; correction now lives where it belongs. Full plan: `docs/V1_5_academic_terms.md`.

**To see it live**, watch the agent logs: `STT keyterm prompting: N terms` on startup, and a `normalized: '…' -> '…'` line when an academic turn is repaired (no line on casual turns — the gate skipping).

---

## Benchmarks

V1 vs V1.5, with results and saved audio in `benchmarks/` (write-up in `benchmarks/RESULTS.md`):

```bash
.venv/bin/python benchmarks/benchmark_normalizer.py   # Layer 2 (text) — needs OPENROUTER_API_KEY
.venv/bin/python benchmarks/benchmark_keyterm.py      # Layer 1 (app-voice audio) — needs CARTESIA + DEEPGRAM
.venv/bin/python tests/test_normalizer.py             # offline gate checks (+ live if key set)
```

Headline (on the app's own Cartesia voice, Devanagari-aware scoring):

| Layer | Metric | V1 → V1.5 |
|---|---|---|
| Layer 1 — keyterm boosting | STT term recovery (48 phrases) | **62% → 82%** (+20) |
| Layer 2 — normalizer | text term recovery (36 phrases) | **41% → 68%** (+27), 0/10 casual turns corrupted |

> Known follow-up: on the app voice a large (~49-term) keyterm list can drop some whole utterances; a ~15-term high-value list matches recovery with zero regressions. See `RESULTS.md`.

---

## Demo deck

A standalone presentation (no server needed):

```bash
open demo/index.html   # navigate with → / ← or click left/right half
```

---

## Mentor modes

Saathi moves between modes mid-conversation and announces every switch out loud:

| Mode | Triggered when |
|---|---|
| Doubt-Solving | Student is stuck on a concept |
| Topic Planning | "kahan se shuru karun" |
| Exam Strategy | Limited days, what to skip |
| Concept Reinforcement | Connecting a doubt to fundamentals |
| Motivation | Confidence dip |
| Energize & Reset | Panic, burnout — breathing or dance break |
| Personal Support | Emotional blocker, not academic |
| Escalation | Serious distress — warm support + helpline |

---

## Docs

Full PRD and phase-by-phase build plan in `/docs`:
- `Saathi_PRD.md` — product vision, principles, three versions
- `00_FOUNDATION.md` — brain build plan (phases 0.1–0.7)
- `V1_browser_mentor.md` — browser channel (phases 1.1–1.4) ✅
- `V1_5_academic_terms.md` — academic-term recognition (keyterm + normalizer) ✅
- `V2_phone_vobiz.md` — phone channel via Vobiz
- `V3_video_whiteboard.md` — video room + whiteboard
