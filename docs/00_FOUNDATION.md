# Foundation — The Mentor Brain (build once)

Goal: a single, runnable voice agent that already behaves like Saathi — knows the student, switches modes, banters, can run breathing/dance resets — **testable in the terminal before any frontend exists.** V1/V2/V3 only add channels around this.

> Most of Saathi's intelligence lives in the **system prompt + injected context**, not in code. Keep code thin: pipeline wiring, profile/memory loading, a few function tools, and state injection. Nothing more.

---

## Phase 0.1 — Repo bootstrap

▶ **Quote to Claude Code:**
> Bootstrap a minimal LiveKit Agents (Python) project for a voice agent. Prefer the official LiveKit `agent-starter-python` layout. Use a virtual env, pin dependencies, and create `.env.local` with placeholders for: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, the LLM key, the STT key, and the TTS key. Do not add anything beyond a runnable agent skeleton. Provide a one-line run command for terminal/console mode.

✅ **Accept when:**
- Project runs in LiveKit console/dev mode and connects to LiveKit Cloud.
- No extra services, Docker, or frameworks were added.
- `.env.local` lists exactly the keys above and nothing speculative.

---

## Phase 0.2 — Config

▶ **Quote to Claude Code:**
> Add one small config module that loads all env vars and exposes the chosen LLM / STT / TTS provider + model names as swappable settings. No hardcoded keys. Default the language behavior to Hindi/Hinglish/English. Keep it to a single file.

✅ **Accept when:**
- Switching an LLM/STT/TTS provider is a one-line config change.
- No keys or model names are hardcoded in the pipeline code.

---

## Phase 0.3 — Student profile

Data contract (sample — keep it this small):
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

▶ **Quote to Claude Code:**
> Create a `profiles/` folder with one sample student profile JSON matching this contract. Add a tiny loader that reads a profile by id and formats it into a concise context string for the system prompt (weak topics, last score, days to exam, language preference). No database, no ORM — a JSON file is the source of truth.

✅ **Accept when:**
- One sample profile exists and loads.
- The formatter produces a short, human-readable context block (not a raw JSON dump).

---

## Phase 0.4 — Memory interface (persistence optional)

▶ **Quote to Claude Code:**
> Define one small memory interface with two operations: get prior-session summary for a student, and save a short summary at session end. Provide a local JSON-file implementation as the default. Add a second implementation backed by Maximem Synap behind the **same interface**, but leave it disabled by default and selectable via config. Do not wire Synap network calls unless the config flag is on.

✅ **Accept when:**
- Default run uses local JSON only and needs no paid credits.
- Swapping to Synap is a config flag, with zero changes to calling code.
- Session-end summary is short (a few lines), not a transcript.

---

## Phase 0.5 — Mentor system prompt (the soul)

This is the most important artifact. It must encode, in prose, all of the following. Have Claude Code draft it from this spec; review it like code.

The prompt must define:
1. **Persona** — a warm, slightly cheeky senior/topper roommate. Uses the student's name. Honest, never condescending.
2. **Language** — reply in the student's language/mix (Hindi/Hinglish/English; Telugu/Tamil if enabled). Mirror code-switching naturally.
3. **Modes** — Doubt-Solving, Topic Planning, Exam Strategy, Concept Reinforcement, Motivation, Energize & Reset, Personal Support, Greeting, Escalation. Instruct it to **announce every mode switch in one short spoken line** before the substance.
4. **Direction-first** — answer the narrow doubt but surface the bigger question; give concrete next steps; for exams, say what to *skip*.
5. **Banter, calibrated** — humour on when mood is light, muted when struggling, **off** under distress. Read the room first.
6. **Energize scripts** — (a) guided breathing paced out loud (box 4-4-4-4 or 4-7-8), breathing *with* the student; (b) a hyped, short, optional dance/movement break with a countdown and a welcome-back; (c) micro-stretch; (d) pre-exam hype-up. All gentle and optional.
7. **Academic-term normalization** — interpret the transcript in math/science context; treat likely mis-hearings ("signs"→"sin x", "cos theta", "lambit karan"→perpendicular) as their intended terms.
8. **Honesty** — never bluff a fact or step; say when unsure. No false outcome guarantees.
9. **Safety/Escalation** — on serious distress, drop banter, stay warm, point to trusted people/helpline support; no clinical advice; age-appropriate always.
10. **Brevity** — conversational turns, no monologues; check in often.

▶ **Quote to Claude Code:**
> Draft the Saathi mentor system prompt covering all 10 requirements in Phase 0.5 of `00_FOUNDATION.md`. Write it as a single, well-organized system prompt string in its own file. Inject the formatted student profile (0.3) and any prior-session summary (0.4) into it at session start. Keep it tight and readable.

✅ **Accept when:**
- All 10 elements are present and unambiguous.
- Mode-switch acknowledgement and banter-calibration rules are explicit.
- Breathing and dance scripts are concrete enough to perform out loud.

---

## Phase 0.6 — Conversation state (lightweight)

Data contract:
```json
{ "mode": "doubt_solving", "subject": "Organic Chemistry", "mood": "frustrated", "last_intent": "asked why SN1 vs SN2" }
```

▶ **Quote to Claude Code:**
> Add a small in-memory session state holding mode, subject, mood, and last_intent. Expose it to the LLM as a single function tool `set_session_state(mode, subject, mood, last_intent)` that the model calls whenever any of these change. Re-inject the current state into the model context each turn. Do not build a separate ML classifier — the LLM is the router. Keep this to one tool and a small state holder.

✅ **Accept when:**
- The model updates state via the tool and the new state visibly influences the next turn.
- No separate routing model or rules engine was added.

---

## Phase 0.7 — Assemble the pipeline

▶ **Quote to Claude Code:**
> Wire the LiveKit Agents session: VAD + turn detection + STT + LLM + TTS, with **interruption/barge-in enabled** and multilingual turn detection on. Inject the system prompt (0.5) + profile (0.3) + memory summary (0.4) + live session state (0.6). On session start, the agent greets the student by referencing their context. On session end, save a short memory summary (0.4). Make it runnable in console mode for terminal testing. Keep the pipeline in one file.

✅ **Accept when:**
- You can talk to Saathi in the terminal with no frontend.
- It opens by referencing the student's profile (not a generic hello).
- You can interrupt it mid-sentence and it stops and follows.
- It can switch modes (doubt→personal), banter when light, and run a breathing reset on request.

---

### Foundation done = the product's brain works. Everything below is just a channel.
