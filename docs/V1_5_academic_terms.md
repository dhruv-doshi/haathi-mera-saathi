# V1.5 — Academic-Term Recognition (proper fix, not a bypass)

Depends on: **Foundation (all of 0.x)** and **V1**. Goal: make Saathi reliably *hear* code-mixed math/science speech ("cos theta", "lambit karan", "sin x" not "signs"). No paid credits beyond the existing LLM/STT keys.

> **Why this version exists.** Indian academic speech is wildly code-mixed — English "cos theta" next to Hindi "lambit karan" (perpendicular) in one sentence — and Deepgram `nova-3` mishears equation components ("sin x" → "signs"). Today the *only* defense is one paragraph in the mentor prompt (`src/prompt.py` "HEARING MATH AND SCIENCE CORRECTLY") asking the LLM to guess through mishearings. That is a **bypass**: the error is never prevented, and correction competes for attention with persona, mood, mode-switching, and safety in a single prompt.
>
> **The real fix is two layers, both already implied by the PRD:**
> 1. **Prevent at the source** — Deepgram nova-3 *keyterm prompting* (a first-class, vendor-supported parameter) seeded with an academic lexicon, so the STT is biased toward the words students actually say.
> 2. **Correct in a dedicated stage** — the **LLM Transcript Normalizer** that PRD §6.7 and the architecture diagram (`NORM` node) already specify but which was never built as a stage. Implement it on LiveKit's `stt_node()` hook (the framework-blessed analog of the existing `llm_node` override), then **remove the responsibility from the mentor prompt**.
>
> **Two confirmed design decisions:** the normalizer is *conditional* (a fast Haiku pass runs only when the transcript looks academic or STT confidence is low — chit-chat passes through with zero added latency); the lexicon is *curated base + profile-extended* (a shared hand-maintained list, auto-extended per session by the student's track and weak topics).

```
audio ─▶ STT (nova-3 + per-session keyterms)            ← Layer 1: prevent at source
      ─▶ stt_node (FINAL_TRANSCRIPT only):
             looks_academic(text) OR confidence < THRESHOLD ?
                ├─ yes → Haiku normalize  (+~150ms, timeout-guarded)   ← Layer 2: §6.7 stage
                └─ no  → pass through     (+0ms)
      ─▶ mentor LLM (no longer responsible for mishearing recovery)
```

---

## Phase 1.5.1 — STT keyterm prevention (Layer 1)

▶ **Quote to Claude Code:**
> Add one new file `src/lexicon.py` holding a curated academic vocabulary and a `build_keyterms(profile: dict) -> list[str]` function. The curated `BASE_LEXICON` covers the terms Indian Class 6–12 / JEE / NEET students actually say — trig (sine, cosine, tangent, theta), calculus (derivative, avkalan, integration, samakalan), Hindi physics (lambit karan = perpendicular, tvaran = acceleration, veg = velocity), and chemistry (SN1, SN2, electrophile). `build_keyterms` returns the base list extended with terms implied by the student's `track` and `weak_topics` (reuse the dict from `profile.load_profile`), deduplicated and capped to Deepgram's keyterm limit. Then change `config.build_stt` to accept `keyterms: list[str] | None = None` and pass it to `deepgram.STT` as `keyterm=...` (nova-3's keyterm prompting parameter — NOT `keywords`, which is nova-2 only). In `agent.py` `entrypoint`, after loading the profile, build the keyterms and pass them into `config.build_stt`. Log the count of keyterms sent. Keep it minimal — no new dependencies, no data-loading framework; the lexicon is plain Python.

✅ **Accept when:**
- The agent starts with no `ValueError` from Deepgram's keyterm/model validation (proves nova-3 accepts the param).
- Logs show a non-zero keyterm count, and the list grows when the profile's `weak_topics` change.
- `config.build_stt()` with no argument still works (keyterms optional).

---

## Phase 1.5.2 — Dedicated normalizer stage (Layer 2, the §6.7 node)

▶ **Quote to Claude Code:**
> Add one new file `src/normalizer.py` with two functions. (1) `looks_academic(text: str) -> bool` — a cheap, dependency-free gate that returns true if the text contains any lexicon term, a math token (a digit, a lone `x`, `theta`, `sin`/`cos`/`tan`/`log`), or a common mishear token (`signs`, `sine`, `co's`, `cosec`). No LLM cost. (2) `async normalize(text, lexicon, llm) -> str` — a single fast-model (Haiku) call at temperature 0 with a tight system prompt: *"You correct raw speech-to-text from an Indian academic voice tutor. Fix ONLY misheard math/science terms (English and Hindi code-mixed); preserve the student's exact language mix and every non-academic word verbatim; make minimal edits; if unsure, leave it unchanged; output ONLY the corrected transcript and nothing else."* Pass the session lexicon as reference context. Guardrails are mandatory: a ~400ms timeout that falls back to the raw text, it must never raise into the voice loop, and it logs `raw → corrected` on every call.
>
> In `config.py` add `NORMALIZER_ENABLED = True`, `NORMALIZER_MODEL = "anthropic/claude-haiku-4-5"`, `CONFIDENCE_THRESHOLD = 0.6`, and a `build_normalizer_llm()` that mirrors `build_llm` but uses the fast model. In `agent.py`, store the lexicon and a normalizer LLM on `Assistant`, then add an `async def stt_node(self, audio, model_settings)` override that follows the existing `llm_node` override pattern: iterate `Agent.default.stt_node(self, audio, model_settings)`, and for `FINAL_TRANSCRIPT` events where `looks_academic(text) or alt.confidence < CONFIDENCE_THRESHOLD`, replace `alternatives[0].text` with the normalized text; yield every other event unchanged. Gate the whole override on `NORMALIZER_ENABLED`. Do not touch interim transcripts.

✅ **Accept when:**
- An academic Hinglish turn shows a `raw → corrected` log line and the mentor answers the *corrected* term.
- A non-academic turn ("haan theek hai chalo") shows **no Haiku call** — pass-through, zero added latency.
- Killing the normalizer (timeout or exception) never drops or delays the turn — it falls back to raw text.
- The override mirrors the `llm_node` pattern; no other pipeline wiring changed.

---

## Phase 1.5.3 — Retire the prompt bypass

▶ **Quote to Claude Code:**
> Now that correction lives in a dedicated stage, remove the heavy "HEARING MATH AND SCIENCE CORRECTLY" block from `src/prompt.py` and replace it with a single light fallback line — something like: *"If a technical term still sounds wrong in context, ask a quick clarifying question rather than guessing."* Keep the existing "say math the way a person speaks it" voice guidance. The mentor prompt should no longer carry a list of specific mishearings to recover — that is the normalizer's job.

✅ **Accept when:**
- The mentor prompt no longer enumerates specific mishearings.
- Conversation quality is unchanged in a quick smoke test (greeting, one doubt, one mode switch).

---

## Phase 1.5.4 — Verification (golden set + manual demo)

▶ **Quote to Claude Code:**
> Add `tests/test_normalizer.py` with a golden set of misheard → intended fixtures: "signs of thirty degree" → sine, "kos theta" → cos theta, "co sec x" → cosec, "lambit karan nikalo", "tvaran kya hoga". Assert that (a) `looks_academic` flags each academic case, (b) `normalize` corrects them, and (c) `looks_academic("haan theek hai chalo")` is **False** (proves the pass-through gate). Then walk me through the end-to-end manual demo and fix anything it surfaces.

✅ **Accept when (this is the V1.5 acceptance gate):**
- `.venv/bin/python -m pytest tests/test_normalizer.py` passes, including the pass-through assertion.
- Live: "sin theta ka value kya hota hai 30 degree pe" is heard and answered correctly, with a `raw → corrected` log.
- Live: a casual turn skips the normalizer entirely (gate proven, latency budget held).
- Deepgram accepts the keyterms (no validation error); the prompt bypass is gone.

---

### Out of scope for V1.5
Retraining or fine-tuning STT, per-word equation/LaTeX reconstruction, visual math (that's V3's whiteboard), and any new paid services. This version only makes the *existing* cascaded pipeline hear academic speech correctly.
