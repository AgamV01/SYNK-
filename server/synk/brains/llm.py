"""The hybrid LLM brain.

`decide` is the cheap tick path and simply delegates to a ReactiveBrain — it never
touches a provider, so no I/O happens on the tick. `converse` is the off-tick
deliberative path that may call an LLM provider; with no provider it degrades to
the reactive templated dialogue, so the framework still runs with zero API keys.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Action, ConverseResult, parse_llm_output
from .providers import (
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
    Provider,
    build_prompt,
    resilient_generate,
)
from .reactive import ReactiveBrain

if TYPE_CHECKING:
    from ..perception import Percept
    from ..world import Agent


class LLMBrain:
    def __init__(
        self,
        provider: Provider | None = None,
        reactive: ReactiveBrain | None = None,
        *,
        timeout: float | None = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
    ) -> None:
        self.provider = provider
        self.reactive = reactive or ReactiveBrain()
        self.timeout = timeout
        self.retries = retries

    def decide(self, agent: Agent, percept: Percept) -> Action:
        # Hot path: pure reactive, no provider, no I/O.
        return self.reactive.decide(agent, percept)

    async def converse(
        self, agent: Agent, percept: Percept, utterance: str
    ) -> ConverseResult:
        if self.provider is None:
            return await self.reactive.converse(agent, percept, utterance)
        memories, history, relationships = self._assemble_context(agent)
        prompt = build_prompt(
            personality=agent.personality,
            memories=memories,
            history=history,
            utterance=utterance,
            relationships=relationships,
        )
        text = await resilient_generate(
            self.provider,
            prompt,
            system=self._system_prompt(agent),
            timeout=self.timeout,
            retries=self.retries,
        )
        # On provider failure/timeout (all retries exhausted) degrade to reactive dialogue.
        if text is None:
            return await self.reactive.converse(agent, percept, utterance)
        # Parse a possible structured action; malformed output degrades to speech-only.
        speech, action = parse_llm_output(text)
        return ConverseResult(text=speech, action=action)

    @staticmethod
    def _assemble_context(
        agent: Agent,
    ) -> tuple[list[str], list[tuple[str, str]], list[str]]:
        """Gather recalled memories, conversation history, and relationship sentiment from
        the agent, if it carries them. Duck-typed so each can be attached independently."""
        memories: list[str] = []
        memory = getattr(agent, "memory", None)
        if memory is not None and hasattr(memory, "recall"):
            memories = [item.text for item in memory.recall()]
        history: list[tuple[str, str]] = []
        conversation = getattr(agent, "conversation", None)
        if conversation is not None and hasattr(conversation, "turns"):
            history = [(turn.speaker, turn.text) for turn in conversation.turns]
        relationships: list[str] = []
        rel = getattr(agent, "relationships", None)
        if rel is not None and hasattr(rel, "describe"):
            relationships = rel.describe()
        return memories, history, relationships

    @staticmethod
    def _system_prompt(agent: Agent) -> str:
        name = agent.name or "an NPC"
        return f"You are {name}, a character in a 3D world. Speak in character, briefly."
