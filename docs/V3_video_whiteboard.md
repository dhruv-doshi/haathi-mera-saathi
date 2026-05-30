# V3 — Video Room + Whiteboard (show me)

Depends on: **Foundation (0.x)**, and reuses the **V1 web client** as a base. Goal: a Google-Meet-style room where Saathi explains *and* writes the working onto a shared whiteboard. No paid credits.

> Highest build cost (real-time canvas). Lowest priority — attempt only after V1 (ideally V2) is locked. A scoped-down version where Saathi posts rendered steps (not freehand drawing) is an acceptable demo.

---

## Phase 3.1 — Room with a board surface

▶ **Quote to Claude Code:**
> Extend the V1 web client into a two-pane room: voice (and optional video tiles) on one side, a shared whiteboard canvas on the other. Reuse the existing connection/token flow. Keep it minimal — the whiteboard is a render surface, not a drawing app for the student.

✅ **Accept when:**
- Student joins and talks to Saathi at V1 quality, with a visible board pane.

---

## Phase 3.2 — Board-event contract

Data contract (agent → board, over a LiveKit data channel):
```json
{ "type": "latex", "content": "\\frac{d}{dx}(\\sin x) = \\cos x", "step": 2 }
```
Supported `type` values: `latex`, `text`, `clear`. Keep the schema this small.

▶ **Quote to Claude Code:**
> Define a board-event message sent over a LiveKit data channel using exactly this contract (types: latex, text, clear). Document it in one short comment block. No extra event types.

✅ **Accept when:**
- A test event published from the agent appears on the board.

---

## Phase 3.3 — Agent draws while it talks

▶ **Quote to Claude Code:**
> Give the Foundation agent one function tool `draw(type, content, step)` that publishes a board event (3.2). Update the system-prompt guidance so that in visual subjects, Saathi posts each working step to the board as it narrates it — speech and board stay in sync. Add nothing else to the brain.

✅ **Accept when:**
- For a geometry/derivative problem, steps appear on the board in time with the explanation.

---

## Phase 3.4 — Board renderer

▶ **Quote to Claude Code:**
> In the web client, render incoming board events: `latex` via KaTeX, `text` as a step line, `clear` wipes the board. Append steps in order. Minimal styling — legibility over polish.

✅ **Accept when:**
- Math renders correctly; steps stack in order; clear works.

---

## Phase 3.5 — Visual demo test

▶ **Quote to Claude Code:**
> Help me rehearse: student joins, asks a visual problem (e.g., a geometry construction or an organic mechanism), and Saathi explains by voice while building the figure/steps on the board, still doing mode switches and encouragement as in V1.

✅ **Accept when (V3 acceptance gate):**
- V1-level conversation quality inside the room.
- Board working matches the spoken explanation and updates live.

---

### Out of scope for V3
Interpreting student-drawn input, multi-participant rooms, screen sharing, recording.
