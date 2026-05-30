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

---

## Stack

| Layer | Choice |
|---|---|
| Voice orchestration | LiveKit Agents (Python) |
| STT | Deepgram `nova-3` (multilingual) |
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
│   ├── agent.py          # LiveKit Agents pipeline — the brain
│   ├── config.py         # Provider + model selection (one-line swaps)
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
- `V2_phone_vobiz.md` — phone channel via Vobiz
- `V3_video_whiteboard.md` — video room + whiteboard
