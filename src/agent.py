import logging
from typing import Annotated

from livekit import agents
from livekit.agents import (
    Agent,
    AgentSession,
    RoomInputOptions,
    TurnHandlingOptions,
    function_tool,
)
# Top-level plugin imports register each plugin on the main thread before
# the worker forks — required by LiveKit Agents.
from livekit.plugins import cartesia, deepgram, openai, silero  # noqa: F401
from livekit.plugins.turn_detector.multilingual import MultilingualModel

import config
import memory
from profile import load_profile, format_profile
from prompt import build_system_prompt
from state import SessionState

logger = logging.getLogger("agent")

STUDENT_ID = "aarav"  # single-student demo; no auth in MVP


class Assistant(Agent):
    def __init__(self, instructions: str) -> None:
        super().__init__(instructions=instructions)
        self.session_state = SessionState()
        self._student_id = STUDENT_ID

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
        """Save a short session summary to memory before shutting down."""
        s = self.session_state
        subject_part = f" Subject covered: {s.subject}." if s.subject else ""
        intent_part = f" Last topic: {s.last_intent}." if s.last_intent else ""
        summary = (
            f"Session ended in mode '{s.mode}', student mood was '{s.mood}'."
            f"{subject_part}{intent_part}"
        )
        memory.save_summary(self._student_id, summary)
        logger.info("Session summary saved for %s: %s", self._student_id, summary)

    # ------------------------------------------------------------------
    # State injection — append current state as system message every turn
    # ------------------------------------------------------------------

    def llm_node(self, chat_ctx, tools, model_settings):
        patched = chat_ctx.copy()
        patched.add_message(role="system", content=self.session_state.format())
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

    # Build the full system prompt: mentor persona + student profile + memory
    profile = load_profile(STUDENT_ID)
    profile_str = format_profile(profile)
    prior_summary = memory.get_summary(STUDENT_ID)
    instructions = build_system_prompt(profile_str, prior_summary)

    session = AgentSession(
        stt=config.build_stt(),
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
        agent=Assistant(instructions=instructions),
        room_input_options=RoomInputOptions(),
    )


AGENT_NAME = "haathi-mera-saathi"

if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(entrypoint_fnc=entrypoint, agent_name=AGENT_NAME)
    )
