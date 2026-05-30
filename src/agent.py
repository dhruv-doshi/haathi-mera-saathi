import asyncio
import logging
from typing import Annotated

from livekit import agents
from livekit.agents import (
    Agent,
    AgentSession,
    RoomInputOptions,
    TurnHandlingOptions,
    function_tool,
    stt as stt_events,
)
# Top-level plugin imports register each plugin on the main thread before
# the worker forks — required by LiveKit Agents.
from livekit.plugins import cartesia, deepgram, openai, silero  # noqa: F401
from livekit.plugins.turn_detector.multilingual import MultilingualModel

import config
import learnings
import lexicon
import memory
import normalizer
import safety
from profile import load_profile, format_profile
from prompt import build_system_prompt
from state import SessionState

logger = logging.getLogger("agent")

STUDENT_ID = "aarav"  # single-student demo; no auth in MVP


def _format_recap(recent: list[dict]) -> str:
    """Turn the most-recent session entries (newest first) into a short recap
    for the system prompt's 'what happened last time' slot."""
    if not recent:
        return ""
    labels = ["Last session", "Before that", "Earlier"]
    lines = []
    for i, entry in enumerate(recent):
        summary = (entry.get("summary") or "").strip()
        if not summary:
            continue
        label = labels[i] if i < len(labels) else "Earlier"
        lines.append(f"{label}: {summary}")
    return "\n".join(lines)


class Assistant(Agent):
    def __init__(
        self,
        instructions: str,
        keyterms: list[str] | None = None,
        normalizer_llm=None,
        learnings_llm=None,
        language_pref: str = "Hinglish",
    ) -> None:
        super().__init__(instructions=instructions)
        self.session_state = SessionState()
        self._student_id = STUDENT_ID
        # V1.5: academic-term normalization. keyterms double as the lexicon the
        # gate checks against; normalizer_llm is the fast correction model (None
        # disables the stage).
        self._keyterms = keyterms or []
        self._normalizer_llm = normalizer_llm
        # End-of-session learnings extraction (None disables it).
        self._learnings_llm = learnings_llm
        self._language_pref = language_pref
        # Deterministic safety layer: flips True once distress is detected, so
        # subsequent turns carry the escalation directive.
        self._escalated = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def on_enter(self) -> None:
        """Greet the student by referencing their profile — never a generic hello."""
        await self.session.generate_reply(
            instructions=(
                "Start the conversation now with a warm, personal greeting in the student's "
                "preferred language mix. Pick ONE specific thing to reference — either something "
                "from last session (e.g. the SN1/SN2 practice you assigned) or a profile fact "
                "(e.g. JEE Mains being close, their Physics mock score, Rotational Motion being "
                "shaky). One or two sentences max, then ask what they want to work on tonight. "
                "Do NOT list multiple topics. Do NOT use any markdown or bullet points."
            ),
            allow_interruptions=True,
        )

    async def on_exit(self) -> None:
        """Persist this session to accumulating memory, heuristic-first.

        We write a cheap heuristic entry synchronously first — it always
        succeeds, so memory accumulates even if shutdown cancels the LLM call.
        Then we attempt a richer LLM extraction and, on success, upgrade the
        just-written entry and fold the durable learnings into the `learned`
        delta layer for the next session's prompt.
        """
        s = self.session_state
        subject_part = f" Subject covered: {s.subject}." if s.subject else ""
        intent_part = f" Last topic: {s.last_intent}." if s.last_intent else ""
        heuristic_summary = (
            f"Session ended in mode '{s.mode}', student mood was '{s.mood}'."
            f"{subject_part}{intent_part}"
        )

        # 1. Durable, instant heuristic entry (never blocks, never cancelled).
        memory.append_session(
            self._student_id,
            {
                "summary": heuristic_summary,
                "mode": s.mode,
                "mood": s.mood,
                "subject": s.subject,
                "last_intent": s.last_intent,
                "source": "heuristic",
            },
        )
        logger.info("Heuristic session entry saved for %s", self._student_id)

        # 2. Best-effort LLM upgrade: extract learnings from the transcript.
        if not (config.LEARNINGS_ENABLED and self._learnings_llm is not None):
            return
        transcript = self._build_transcript()
        if not transcript:
            return
        extracted = await learnings.extract_learnings(
            transcript, self._learnings_llm, timeout=config.LEARNINGS_TIMEOUT_S
        )
        if not extracted:
            return  # heuristic entry already persisted; learned layer untouched

        if extracted.get("summary"):
            memory.update_last_session(
                self._student_id, {"summary": extracted["summary"], "source": "llm"}
            )
        updated = learnings.update_learned(
            memory.get_learned(self._student_id), extracted
        )
        memory.save_learned(self._student_id, updated)
        logger.info("LLM learnings saved for %s: %s", self._student_id, updated)

    def _build_transcript(self, max_turns: int = 40, max_chars: int = 6000) -> str:
        """Flatten recent chat history into a plain transcript for extraction."""
        try:
            messages = self.session.history.messages()
        except Exception:
            logger.exception("could not read chat history for learnings")
            return ""
        lines: list[str] = []
        for m in messages:
            role = getattr(m, "role", "")
            if role not in ("user", "assistant"):
                continue
            text = getattr(m, "text_content", None) or getattr(m, "content", "")
            if isinstance(text, list):
                text = " ".join(str(c) for c in text)
            text = (text or "").strip()
            if text:
                lines.append(f"{role}: {text}")
        transcript = "\n".join(lines[-max_turns:])
        return transcript[-max_chars:]

    # ------------------------------------------------------------------
    # Transcript normalization (V1.5, PRD 6.7) — correct misheard math/science
    # terms between STT and the LLM, but only when it's worth it.
    # ------------------------------------------------------------------

    async def stt_node(self, audio, model_settings):
        async for event in Agent.default.stt_node(self, audio, model_settings):
            if (
                config.NORMALIZER_ENABLED
                and self._normalizer_llm is not None
                and event.type == stt_events.SpeechEventType.FINAL_TRANSCRIPT
                and event.alternatives
            ):
                alt = event.alternatives[0]
                low_conf = 0 < alt.confidence < config.CONFIDENCE_THRESHOLD
                if low_conf or normalizer.looks_academic(alt.text, self._keyterms):
                    alt.text = await normalizer.normalize(
                        alt.text,
                        self._keyterms,
                        self._normalizer_llm,
                        timeout=config.NORMALIZER_TIMEOUT_S,
                    )

                # Deterministic safety check on the final (normalized) transcript.
                # Runs regardless of the LLM — see _handle_escalation.
                if config.SAFETY_ENABLED:
                    category = safety.detect_distress(alt.text)
                    if category:
                        self._handle_escalation(category)
            yield event

    # ------------------------------------------------------------------
    # Deterministic safety escalation (does not depend on the LLM complying)
    # ------------------------------------------------------------------

    def _handle_escalation(self, category: str) -> None:
        """Force escalation and guarantee the helpline is spoken.

        Called synchronously from stt_node. State mutation happens immediately;
        the spoken helpline is dispatched as a task so the STT stream is never
        blocked.
        """
        logger.warning("SAFETY: distress detected (category=%s) — escalating", category)
        # 1. Force escalation mode + flag. llm_node re-injects state every turn,
        #    so this propagates to the model without its cooperation.
        self.session_state.update(mode="escalation")
        self._escalated = True
        # 2. Speak the fixed helpline line via TTS only (no LLM round-trip), so
        #    the number 14416 can never be dropped, paraphrased, or refused.
        asyncio.create_task(self._say_helpline())

    async def _say_helpline(self) -> None:
        try:
            self.session.interrupt()
            await self.session.say(
                safety.helpline_line(self._language_pref),
                allow_interruptions=False,
            )
        except Exception:
            logger.exception("SAFETY: failed to speak helpline line")

    # ------------------------------------------------------------------
    # State injection — append current state as system message every turn
    # ------------------------------------------------------------------

    def llm_node(self, chat_ctx, tools, model_settings):
        patched = chat_ctx.copy()
        patched.add_message(role="system", content=self.session_state.format())
        # Once the deterministic safety layer has fired, keep the conversation
        # that wraps the spoken helpline in a safe register on every later turn.
        if self._escalated:
            patched.add_message(role="system", content=safety.ESCALATION_DIRECTIVE)
        return Agent.default.llm_node(self, patched, tools, model_settings)

    # ------------------------------------------------------------------
    # The single tool the LLM calls to update conversation state
    # ------------------------------------------------------------------

    @function_tool
    async def set_session_state(
        self,
        mode: Annotated[
            str,
            "current mentor mode — one of: greeting, doubt_solving, topic_planning, "
            "exam_strategy, concept_reinforcement, motivation, energize_reset, "
            "personal_support, escalation",
        ],
        mood: Annotated[
            str,
            "detected student mood — e.g. neutral, frustrated, anxious, motivated, panicked, sad",
        ],
        subject: Annotated[
            str, "active subject or topic being discussed, empty string if none"
        ] = "",
        last_intent: Annotated[
            str, "one-line description of what the student just asked or said"
        ] = "",
    ) -> str:  # LLM may pass None for optional params — guard below
        """Call this whenever the mode, mood, subject, or student intent changes.
        Keep the mentor aware of where the conversation is at all times.
        """
        self.session_state.update(
            mode=mode or "",
            mood=mood or "",
            subject=subject or "",
            last_intent=last_intent or "",
        )
        logger.debug("State → %s", self.session_state.format())
        return f"State updated: {self.session_state.format()}"


async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    # Build the full system prompt: mentor persona + student profile + memory.
    # The profile seed is merged with the accumulated `learned` delta layer, and
    # the opening recaps the last few sessions — so Saathi reflects real progress.
    profile = load_profile(STUDENT_ID)
    learned = memory.get_learned(STUDENT_ID)
    profile_str = format_profile(profile, learned)
    prior_summary = _format_recap(memory.get_recent(STUDENT_ID, n=config.MEMORY_RECENT_N))
    instructions = build_system_prompt(profile_str, prior_summary)

    # V1.5 — academic-term recognition. Keyterms bias the STT at the source;
    # the normalizer LLM corrects what still slips through.
    keyterms = lexicon.build_keyterms(profile)
    logger.info("STT keyterm prompting: %d terms", len(keyterms))
    normalizer_llm = config.build_normalizer_llm() if config.NORMALIZER_ENABLED else None
    learnings_llm = config.build_learnings_llm() if config.LEARNINGS_ENABLED else None

    session = AgentSession(
        stt=config.build_stt(keyterms=keyterms),
        llm=config.build_llm(),
        tts=config.build_tts(),
        vad=silero.VAD.load(),
        turn_handling=TurnHandlingOptions(
            turn_detection=MultilingualModel(),
            allow_interruptions=True,
        ),
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(
            instructions=instructions,
            keyterms=keyterms,
            normalizer_llm=normalizer_llm,
            learnings_llm=learnings_llm,
            language_pref=profile.get("language_pref", "Hinglish"),
        ),
        room_input_options=RoomInputOptions(),
    )


AGENT_NAME = "haathi-mera-saathi"

if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(entrypoint_fnc=entrypoint, agent_name=AGENT_NAME)
    )
