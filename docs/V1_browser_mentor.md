# V1 — Browser Voice Mentor (the product)

Depends on: **Foundation (all of 0.x).** Goal: let a student talk to Saathi in a browser. No paid credits.

> If you only ship V1, you've shipped the product. Spend effort on conversation quality, not UI polish.

---

## Phase 1.1 — Token endpoint

▶ **Quote to Claude Code:**
> Add a tiny token endpoint that mints a LiveKit access token for a given room + participant identity using the LiveKit API key/secret from env. One small file, one route. No auth, no user system — this is a single-student MVP.

✅ **Accept when:**
- Hitting the endpoint returns a valid join token.
- Nothing beyond token minting was added.

---

## Phase 1.2 — Minimal web client

▶ **Quote to Claude Code:**
> Create a minimal single-page web client in `/web` using the LiveKit JS client SDK that: fetches a token (1.1), connects to a room, publishes the mic, plays the agent's audio, and shows a live transcript of both sides. Plain HTML/JS (or one small component) — no build tooling unless strictly required. Add a single "Talk to Saathi" button to start.

✅ **Accept when:**
- Clicking the button connects and you hear Saathi.
- Transcript shows both student and mentor turns.
- No heavyweight frontend framework or bundler was introduced unnecessarily.

---

## Phase 1.3 — Agent dispatch

▶ **Quote to Claude Code:**
> Ensure the Foundation agent automatically joins the room when a student connects (LiveKit agent dispatch). The same brain from Foundation must run unchanged — this phase only connects it to the browser room.

✅ **Accept when:**
- Joining from the browser triggers Saathi to join and greet with the student's context.
- Interruption/barge-in works over the browser audio path.

---

## Phase 1.4 — Demo hardening

▶ **Quote to Claude Code:**
> Add nothing new. Help me rehearse and fix issues for this demo flow: (1) Saathi greets referencing the profile; (2) student asks a Hinglish doubt with a math term; (3) student pivots to "I feel behind" — Saathi reads the mood, drops banter, supports; (4) student sounds panicked — Saathi runs a short breathing reset; (5) student is ready — Saathi gives one concrete next step. Fix any mode-switch, latency, or transcript bugs surfaced.

✅ **Accept when (this is the V1 acceptance gate):**
- Opening references the student's context.
- A mid-explanation interruption + redirect works.
- ≥3 intents handled in one session, each switch verbally acknowledged.
- Banter appears when light, absent under distress.
- A guided breathing and/or dance reset runs on cue.
- Hinglish + embedded math term understood correctly.
- No monologues without a check-in.

---

### Out of scope for V1
Phone, video, whiteboard, accounts, dashboards. Persistent cross-call memory only if you flipped on Synap in Foundation 0.4.
