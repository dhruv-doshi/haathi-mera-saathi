# Saathi — Build Index & How To Use These Plans

This folder turns the PRD into an executable build. You drive [Claude Code](https://claude.com/claude-code); these files are the scripts you quote from.

## Files
| File | What it builds | Depends on |
|---|---|---|
| `Saathi_PRD.md` | Product spec (the why/what) | — |
| `00_FOUNDATION.md` | The shared **Mentor Brain** + runnable terminal agent. Build once. | — |
| `V1_browser_mentor.md` | Browser voice mentor (the product) | Foundation |
| `V2_phone_vobiz.md` | Same mentor on a real phone number | Foundation |
| `V3_video_whiteboard.md` | Same mentor in a video room with a shared whiteboard | Foundation |

## Build order
1. **Foundation (Phase 0.x)** — must be done first; ends with an agent you can talk to in the terminal.
2. **V1 (Phase 1.x)** — wrap the agent in a browser. This alone is the product.
3. **V2 (Phase 2.x)** *or* **V3 (Phase 3.x)** — add a channel only after V1 is solid.

## How to use with Claude Code
- Work **one phase at a time**. Each phase has a **▶ Quote** block (paste that to Claude Code) and an **✅ Accept when** list (your review checklist before moving on).
- Tell Claude Code at the start of a session: *"Read `Saathi_PRD.md` and `00_FOUNDATION.md` for context. We are building phase X. Keep it minimal — no speculative abstraction, no extra files, no frameworks I didn't ask for."*
- Reject anything that adds dependencies, config, or layers a phase didn't ask for. Lightweight is a hard requirement.

## Recommended stack (all swappable, all lightweight)
- **Orchestration:** LiveKit Agents (Python) — built-in VAD, turn detection, interruption; cascaded STT→LLM→TTS pipeline so we can modify LLM output (needed for our state + normalization logic).
- **Realtime infra:** LiveKit Cloud free tier (not a Vobiz/Maximem credit).
- **LLM:** one fast, capable model, swappable via env (Claude or GPT-4-class).
- **STT:** Indian-language-capable model (Deepgram multilingual or Sarvam). **TTS:** expressive multilingual voice (ElevenLabs or Sarvam) — expressiveness matters for banter/energy.
- *Simplification option:* LiveKit Inference exposes STT/LLM/TTS behind a single LiveKit key if you want fewer accounts. Use it only if it reduces setup.

## Credit discipline (carried from the PRD)
- Foundation, V1, V3: **no paid credits** (LiveKit free tier + your LLM/STT/TTS keys).
- V2: **Vobiz** (telephony) — the only credit genuinely required, and only for the phone channel.
- **Maximem Synap:** optional, only if you want persistent cross-call memory (see Foundation Phase 0.4). Off by default.

## Suggested repo layout (let Claude Code create only what each phase needs)
```
/agent          # python agent (Mentor Brain + pipeline)
/web            # minimal frontend(s) for V1 and V3
/profiles       # sample student profile JSON
*.md            # PRD + these build plans
.env.local      # keys (never commit)
```
