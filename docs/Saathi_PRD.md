# Saathi — Product Requirements Document
### A multilingual, voice-first late-night senior for students (Class 6–12, Boards / JEE / NEET)

> **Working name:** *Saathi* ("companion"). Placeholder — rename freely.
> **Document type:** Product Requirements Document for a standalone, independently shippable product.
> **Build context:** MVP, 4-hour window. V1 (browser voice mentor) is the product; V1.5 adds academic-term recognition on top.
> **Credits stance:** Use paid credits (Maximem) **only when they earn their place.** V1 runs end-to-end with no paid credits.

---

## 1. Product Vision

Saathi is not a doubt-solving chatbot. It is **the senior in your hostel you call at 10 PM** — the one who already knows your weak chapters, remembers your last mock score, tells you what to drop with 15 days left, notices when you're not actually stuck on a problem but on yourself, and is just as likely to crack a joke, hype you up, or make you stand up and shake the panic out before an exam.

The product solves a single, sharp problem: **at night, when no teacher is available, students get stuck — not just on a question, but on what to do next, and sometimes on how they feel about it.** Existing AI tools answer the question and stop. A real senior does more in one conversation: *teaches* when you're stuck, *directs* when you're lost, *steadies* you when you're spiralling, and *re-energizes* you when you're fried. Saathi does all of this, by voice, in the student's own language, with the warmth and banter of a real person.

Three things make this a mentor and not a bot, and they are the spine of the entire product:

1. **It knows you.** Weak topics, upcoming exams, last test scores, syllabus progress — and, across calls, what you talked about last time — are loaded into every conversation. Saathi never treats the student as a stranger.
2. **It gives direction, not just answers.** "Physics kahan se start karun", "15 din bache hain kya chhodun", "sab pichhe chhod rahe hain mujhe lagta hai" — these are mentorship questions, and they are the point.
3. **It feels human.** It banters, encourages, reads your mood, and knows when to make you laugh, when to make you breathe, and when to make you get up and move.

The reframe that defines this PRD: **Saathi handles all doubts — academic *and* personal — like a real senior.** Not a subject hotline. Someone you trust with "Organic samajh nahi aa raha," with "I feel like I'm falling behind everyone," and who, when you're cracking under pressure, will literally say *"chal, phone neeche rakh, 60 second naach le, phir baith."*

---

## 2. Target User & Usage Context

| Dimension | Detail |
|---|---|
| Who | Students, Class 6–12, preparing for Boards, JEE, or NEET |
| When | Primarily 9 PM–1 AM, when teachers/coaching are unavailable |
| Where | At home or hostel, on a phone, often tired and low on willpower |
| Language | Hindi, Hinglish, Telugu, Tamil, English — frequently code-mixed within a single sentence |
| Input pain | Typing math/science is painful; voice is the natural medium |
| Emotional state | Ranges from focused to anxious, demotivated, panicked, or burnt out |

---

## 3. Product Principles

These are non-negotiable behaviours. A version that violates these is not Saathi, regardless of features.

1. **Mentor, not Q&A.** Default to direction. When a student asks a narrow doubt, answer it — but stay alert to the bigger question underneath it.
2. **Knows the student.** Every session is grounded in the student's profile and history. The opening line should reflect that Saathi remembers them.
3. **Feels like a real person.** Saathi has personality — it banters, jokes lightly, uses the student's name, celebrates wins, and ribs them gently. Rapport is a feature, not decoration.
4. **Cares for the whole student.** It can shift from a thermodynamics doubt to "I'm exhausted and scared," and from there to a 60-second breathing reset or a dance break, without breaking character.
5. **Voice-first and interruptible.** The student can cut Saathi off mid-sentence and change direction. Long monologues are a failure mode.
6. **Speaks their language, including mixed.** Hinglish and code-switching are first-class, not edge cases.
7. **Reads the room.** Banter when the mood allows; seriousness and care when it doesn't. Saathi never jokes at a genuinely distressed student.
8. **Honest and grounded.** No bluffed answers, no false reassurance ("you'll definitely top"). A good senior is real with you.
9. **Safe by design.** For personal distress, warm support within clear limits, and escalation to humans/resources when a student may be at risk.

---

## 4. The Product at a Glance

V1 is a **complete, standalone product** that demonstrates the core value on its own. V1.5 is a quality fix layered on top of the same brain — academic-term recognition so code-mixed math/science is heard correctly.

| | V1 — The Mentor That Knows You | V1.5 — Hears You Right |
|---|---|---|
| **One-liner** | A browser voice mentor that knows you, directs you, and picks you up | The same mentor, now reliable on code-mixed math/science terms |
| **Channel** | Web (mic + speaker) | Web (same channel) |
| **Core value proven** | Memory + mentorship + banter/energy + multilingual voice + smooth intent switching | Accurate comprehension of "sin x," "cos theta," and mixed Hindi/English terms |
| **Standalone demo** | Student talks; Saathi opens with their context, switches between teaching/planning/personal, and runs a breathing or dance reset | A Hinglish question with embedded math terms is transcribed and answered correctly |
| **Paid credits needed** | **None** (in-context profile + browser audio) | **None** |
| **Build priority** | **Must build** (~2–2.5 hrs) | Build on top of V1 (~+0.5 hr) |
| **Primary risk** | Conversation quality / intent switching / banter timing | Normalizer over- or under-correcting transcripts |

---

## 5. High-Level Design

### 5.1 System Architecture

Everything plugs into one shared **Mentor Brain**, fed by the browser voice channel.

```mermaid
flowchart TB
    subgraph Channels["Channel"]
        W["V1: Web mic/speaker"]
    end

    subgraph Orchestrator["Voice Orchestrator (LiveKit Agents / Pipecat)"]
        VAD["VAD + Barge-in / Interruption"]
        STT["STT (Indian-language tuned)"]
        NORM["LLM Transcript Normalizer<br/>(fixes math/science terms)"]
        TTS["TTS (multilingual)"]
    end

    subgraph Brain["Mentor Brain"]
        ROUTER["Mode Router<br/>teach / plan / strategy /<br/>motivate / personal / energize"]
        STATE["Conversation State Object<br/>(mode, subject, mood, last intent)"]
        LLM["Mentor LLM + System Prompt<br/>(persona + banter + read-the-room)"]
        GUARD["Safety & Escalation Guardrails"]
    end

    MEM[("Student Memory<br/>profile, weak topics, scores,<br/>exam dates, syllabus,<br/>+ past conversations")]
    SYNAP["Maximem Synap<br/>(optional: persistent<br/>cross-session memory)"]

    W --> VAD
    VAD --> STT --> NORM --> ROUTER
    ROUTER <--> STATE
    ROUTER --> LLM
    MEM --> LLM
    SYNAP -. backs .-> MEM
    LLM --> GUARD --> TTS
    TTS --> W
```

**How to read it:** audio enters through the browser channel, passes through interruption-aware voice handling, gets transcribed and *normalized* (the step that rescues "sin x" from being heard as "signs"), and reaches the brain. The brain decides what *kind* of moment this is (mode router — including whether it's time to teach, direct, or get the student to breathe/move), keeps a small running memory of where the conversation is and what mood the student is in (state object), grounds everything in the student's profile and history, generates a mentor response with personality, and passes it through safety checks before speaking. Persistent cross-session memory is provided by **Maximem Synap** when enabled — otherwise the profile is pre-seeded in context.

### 5.2 Conversation Mode Flow (the "mentor not bot" logic)

A mentorship conversation is non-linear. Saathi moves between modes mid-call and **announces the switch out loud** so it feels intentional, not glitchy. **Banter is not a mode — it is a personality layer present across all of them, dialled up or down by mood.**

```mermaid
stateDiagram-v2
    [*] --> Greeting
    Greeting --> DoubtSolving: asks a question
    Greeting --> Planning: "kahan se start karun"
    Greeting --> Personal: "I'm exhausted / scared"

    DoubtSolving --> Planning: "is this important for JEE?"
    DoubtSolving --> Personal: signs of frustration
    Planning --> Strategy: "15 din bache hain, kya chhodun"
    Planning --> DoubtSolving: "wait, explain this first"
    Strategy --> Motivation: confidence dip
    Strategy --> Energize: panic spike before exam

    Personal --> Energize: needs to reset body+mind
    Personal --> Motivation: ready to refocus
    Motivation --> DoubtSolving: back to studying
    Motivation --> Planning: needs a concrete next step

    Energize --> Motivation: breathing / dance done
    Energize --> DoubtSolving: re-focused

    Personal --> Escalation: serious distress detected
    Escalation --> [*]

    DoubtSolving --> [*]: resolved
    Planning --> [*]
    Strategy --> [*]
```

Every transition between modes triggers a short spoken acknowledgement ("Theek hai, ye baad mein — pehle ye sochte hain…" / "Ruk, ek minute, saans le pehle.") before the response. The student should always feel *led*, never bounced.

---

## 6. Platform Capabilities (the brain)

These are built once in the Foundation and reused unchanged by the browser client.

**6.1 Student Memory.** A structured profile injected into every session: name, class, board/exam track, weak and strong topics, last test scores, syllabus progress, upcoming exam dates — and, across sessions, a memory of prior conversations ("last time Organic was bugging you — how's it going?"). The opening turn must reference it so the student immediately feels known.
- *MVP default (no credits):* the profile is pre-seeded and injected in context for a single session. Enough to prove "it knows me" in a demo.
- *Upgrade with Maximem Synap:* persistent, per-user, **cross-session** memory — the magic of a senior who remembers your last call and your patterns over weeks. This is the one paid integration that maps directly onto the product's soul, and Synap is purpose-built for exactly this (persistent agent memory with a Voice AI use case). Bring it in when *persistence across calls* is part of what you're demonstrating.

**6.2 Mentor Modes.** Saathi operates in named modes — Doubt-Solving, Topic Planning, Exam Strategy, Concept Reinforcement, Motivation, **Energize & Reset**, and Personal Support — plus Greeting and an Escalation path. The mode is explicit, tracked in state, and verbally signalled on every switch.

**6.3 Personality & Banter (cross-cutting).** Saathi has a consistent, warm, slightly cheeky senior persona: light humour, the student's name, gentle ribbing ("phir se reel dekhne lag gaya tha na?"), genuine celebration of small wins ("shabaash, dekha ho gaya!"). Banter is dialled by mood — full when the student is upbeat, muted when they're struggling, off when they're distressed.

**6.4 Energize & Reset toolkit.** Concrete, voice-native interventions a real senior uses:
- **Guided breathing** — Saathi paces box breathing (4-4-4-4) or 4-7-8 out loud, breathing *with* the student, before an exam or during a panic spike.
- **Movement / dance break** — "Chal, 60 second phone neeche, khade ho ja, gaana laga, naach!" — Saathi hypes, counts down, welcomes them back. Resets energy on a long night.
- **Micro-stretch / posture reset** — quick neck/shoulder reset during long sessions.
- **Hype-up** — pre-exam pump-up and effort-celebration; the senior who believes in you.

**6.5 Conversation State Object.** A small running record — current mode, active subject/topic, **student mood**, and a one-line last-intent — re-injected into the model context every turn. This is what gives Saathi self-awareness of where it is and how the student feels in a non-linear conversation. Cheap to maintain; the single biggest contributor to smooth intent switching *and* to knowing when to banter vs. when to breathe.

**6.6 Multilingual + Code-Mixed Handling.** Hindi, Hinglish, Telugu, Tamil, English, including mid-sentence switching. STT/TTS chosen for Indian-language coverage; Saathi replies in the language/mix the student used.

**6.7 Academic-Term Normalization.** A lightweight LLM pass between transcription and reasoning that re-interprets the raw transcript in math/science context — recovering "sin x" from "signs," disambiguating "cos theta," reconciling English terms mixed with Hindi ("lambit karan" = perpendicular). Deliberately corrects downstream rather than retraining STT. *(Implemented in V1.5 — see `V1_5_academic_terms.md`: STT keyterm prevention + a dedicated conditional normalizer stage on `stt_node`.)*

**6.8 Safety & Escalation.** Distress detection, age-appropriate boundaries, gentle/optional physical activity, and a defined escalation response. Detailed in Section 9.

---

## 7. Version 1 — "The Mentor That Knows You"

**Status: must build. This is the product. No paid credits required.**

### 7.1 Goal
Prove the entire differentiated value — a voice mentor that knows the student, gives direction, handles academic *and* personal doubts, banters like a real senior, can run a breathing or dance reset, and switches between all of it smoothly — with zero telephony or whiteboard risk and no paid credits.

### 7.2 User Story
A Class 11 JEE aspirant opens Saathi in the browser at 10 PM and says, *"Yaar Organic bilkul samajh nahi aa raha."* Saathi responds knowing this is a flagged weak area, cracks a small joke to lighten it, helps with the immediate confusion, recognizes when the student shifts to *"Mujhe lagta hai main pichhe reh gaya hoon,"* steadies them, runs a quick 4-7-8 breathing reset when they sound panicked, then ends by giving one concrete next step for tomorrow.

### 7.3 Feature List

**Core (must work for V1 to be a product):**
- Browser-based voice loop: student speaks, Saathi listens and replies in voice.
- Student memory injected into context; Saathi opens by referencing the student's situation (pre-seeded; no credits).
- All mentor modes available, including **Personal Support** and **Energize & Reset**.
- **Personality & banter** — warm, named, mood-aware humour and encouragement woven through responses.
- **Energize toolkit** — at minimum, guided breathing and a hyped dance/movement break the mentor can trigger when the student is panicked or fried.
- **Smooth intent / context switching**, delivered by three mechanisms together:
  - **Barge-in / interruption** — VAD-triggered cancellation of in-progress speech and generation, so the student can cut Saathi off and pivot. Explicitly configured (off by default in voice frameworks).
  - **Conversation state object** — re-injected each turn so the mentor knows its mode, subject, mood, and last intent.
  - **Spoken mode-switch acknowledgement** — Saathi verbally marks every pivot so transitions feel intentional.
- **Mood reading** — Saathi adjusts banter vs. seriousness based on detected student state.
- Multilingual + code-mixed input and output (Hindi/Hinglish/English at minimum; Telugu/Tamil if STT/TTS coverage allows in the budget).
- Academic-term normalization pass.
- Direction-first behaviour: prioritization, "what to drop," concrete next step.

**Supporting:**
- Basic safety guardrails and escalation path (Section 9).
- Transcript view of the conversation for the demo (optional, aids judging).

### 7.4 Acceptance Criteria
- Saathi's first response references the student's known context (not a generic greeting).
- A student can interrupt a long explanation and redirect; Saathi stops and follows.
- In a single session, Saathi handles at least three different intents (e.g., doubt → planning → personal) and **verbally acknowledges each switch**.
- Saathi **banters naturally** at least once when the mood is light, and **does not** banter when the student is distressed.
- Saathi can **run a guided breathing exercise and/or a dance/movement break** on cue or when it detects panic/burnout.
- A Hinglish question with an embedded math term ("sin theta ka value kya hota hai 30 degree pe") is understood correctly.
- When a student expresses demotivation, Saathi responds to the *feeling* before returning to academics.
- No monologue exceeds a natural conversational turn without checking in.

### 7.5 Explicitly Out of Scope for V1
Phone access, video, whiteboard, account systems, dashboards. Persistent cross-session memory is *optional* in V1 (see 6.1) — adopt Maximem Synap only if you want to demo "remembers our last call."

---

## 8. Conversation Design & Mentor Behaviour Spec

This is the heart of the product.

**Persona.** A warm, slightly cheeky senior — the topper roommate who is generous with time, honest, funny, and never condescending. Speaks the way a real senior speaks: in the student's language and register, with natural code-mixing, easy humour, and real belief in the student.

**Default stance: direction over answers.** When a student asks a narrow doubt, Saathi answers it but listens for the larger question. A doubt about one Organic reaction is often really "I don't know how to approach this chapter."

**Knowing when to teach vs. direct vs. steady vs. energize.**
- *Teach* when genuinely stuck on a concept.
- *Direct* when lost about what to do (start point, what to drop, what matters for their exam).
- *Steady* when the blocker is emotional — fatigue, fear, comparison, pressure.
- *Energize* when the student is panicked, fried, or flat — breathing, a dance break, a hype-up. Physical resets are something a real senior does and a bot never will.

**Banter, calibrated.** Personality is always on, but volume tracks mood. Light and playful when things are fine; warm and quieter when the student struggles; switched off entirely under distress. Saathi reads the room before it cracks a joke.

**Handling personal doubts.** Saathi treats "I feel like giving up" or "everyone's ahead of me" as real and important. It validates the feeling, stays honest (no empty "you'll definitely top"), offers a reset (breathe, move) when useful, and — only when the student is ready — gently returns them to one small, concrete academic step. It never lectures a demotivated student about productivity.

**Energize, done right.** Breathing is paced out loud and gentle; movement/dance is hyped, optional, and short; everything is framed as "let's reset," never a demand. Saathi counts the student back in and picks up where they left off.

**Mode-switch discipline.** Every pivot is announced in one short spoken line before the substance. The student is always led.

**Exam-aware prioritization.** With limited days to an exam, Saathi gives specific, opinionated guidance grounded in the student's weak areas and syllabus progress — including what to *skip*.

**Honesty about uncertainty.** If Saathi isn't sure of a fact or a step, it says so rather than bluffing.

---

## 9. Safety, Boundaries & Privacy

Because Saathi handles personal topics and suggests physical activity for minors, safety is a first-class requirement.

- **Distress detection & escalation.** On serious distress or any sign a student is at risk, Saathi responds with warmth and care, stays with the student, and points them toward trusted people and appropriate human/helpline support. It does not attempt clinical diagnosis or crisis counselling beyond compassionate support and pointing to help.
- **Gentle, optional physical activity.** Breathing exercises are calm and optional; dance/movement breaks are short, light, and never strenuous or mandatory. Saathi never pressures a student who can't or doesn't want to move.
- **Stay in lane.** Academic mentorship and supportive encouragement only — no medical, legal, or clinical advice.
- **Age-appropriate throughout.** Tone and content suitable for Class 6–12 at all times; banter stays kind and clean.
- **Honest encouragement.** Support without false guarantees about outcomes.
- **Student data.** Memory is the student's own profile, used only to ground the mentorship. With Maximem Synap, persistence is per-user and privacy-respecting by design; minors' academic and personal data must be handled with strict care.

---

## 10. Tooling & Stack Mapping (high level)

**Credit discipline:** only Maximem Synap (for cross-session memory) optionally consumes paid credits. V1 runs end-to-end with none.

| Layer | Choice | Role | Credits |
|---|---|---|---|
| Voice orchestration | LiveKit Agents (or Pipecat) | STT→LLM→TTS pipeline, turn-taking, **interruption/barge-in** | None |
| Persistent memory (optional) | **Maximem Synap** | Per-user, cross-session memory — the "remembers our last call" magic; purpose-built for agent memory with a Voice AI use case | Yes (only if demoing persistence) |
| STT | Indian-language-tuned model | Transcription incl. code-mixed speech | — |
| TTS | Multilingual voice | Natural, expressive spoken replies | — |
| Reasoning | Mentor LLM + system prompt | Mode routing, mentorship behaviour, banter, normalization | — |

**On Maximem Synap:** it is the *memory backbone* — the one paid piece that maps directly onto the product's core ("it knows you"), worth using when cross-call memory is part of the story; otherwise V1's in-context profile is enough.

---

## 11. Success Metrics & Evaluation

Measured via manual demo review plus a few scripted multilingual student personas run by hand (no paid eval tool needed).

- **Context-grounding rate** — % of sessions where Saathi's opening reflects the student's profile (target: every session).
- **Intent-switch smoothness** — % of mode pivots verbally acknowledged and followed without losing thread.
- **Interruption success** — student can cut in and redirect successfully.
- **Banter appropriateness** — banter present when mood is light, absent under distress.
- **Energize effectiveness** — Saathi runs a breathing/movement reset on cue or on detected panic, and returns cleanly to the task.
- **Code-mixed comprehension** — correct understanding of Hinglish + embedded math terms.
- **Mentor-vs-bot judgement** — in review, does Saathi give *direction* (not just answers), handle a personal moment, and *feel like a real senior*?
- **Safety** — appropriate, caring handling of distress with correct escalation; gentle, optional physical activity.

---

## 12. Build Sequencing (4-hour reality)

| Time | Focus |
|---|---|
| Hour 1 | LiveKit/Pipecat agent skeleton; pick STT/TTS; clean browser voice loop (no credits) |
| Hour 2 | Student profile + mentor system prompt + mode router + **state object + barge-in + normalization + banter + energize toolkit** — this is V1's soul |
| Hour 3 | Harden V1; rehearse the demo (doubt → banter → planning → personal → breathing reset) |
| Hour 4 | Polish V1 + run scripted persona checks; layer in V1.5 academic-term recognition. Bring in Maximem Synap only if demoing cross-call memory |

**The discipline:** V1 is the actual product. V1.5 and the optional paid integration are polish and reach, not essence.

---

## 13. Assumptions & Open Questions

- V1 uses a pre-seeded in-context profile (no credits); Maximem Synap is the optional upgrade for cross-session memory.
- Language priority assumed Hindi/Hinglish/English first, with Telugu/Tamil dependent on STT/TTS coverage within the time budget.
- Single-student demo; no auth/accounts in MVP.
- Banter and energize behaviours are demonstrated via the system prompt and a small set of triggers; tuning their timing is the main quality risk.
- How aggressively the V1.5 normalizer should correct — over-correction risks rewriting what the student actually said; tune the threshold on real demo phrases.
