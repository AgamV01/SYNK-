"""The hybrid LLM brain.

`decide` is the cheap tick path and simply delegates to a ReactiveBrain — it never
touches a provider, so no I/O happens on the tick. `converse` is the off-tick
deliberative path that may call an LLM provider; with no provider it degrades to
the reactive templated dialogue, so the framework still runs with zero API keys.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Action, ConverseResult
from .providers import Provider, build_prompt
from .reactive import ReactiveBrain

if TYPE_CHECKING:
    from ..perception import Percept
    from ..world import Agent


class LLMBrain:
    def __init__(
        self,
        provider: Provider | None = None,
        reactive: ReactiveBrain | None = None,
    ) -> None:
        self.provider = provider
        self.reactive = reactive or ReactiveBrain()

    def decide(self, agent: Agent, percept: Percept) -> Action:
        # Hot path: pure reactive, no provider, no I/O.
        return self.reactive.decide(agent, percept)

    async def converse(
        self, agent: Agent, percept: Percept, utterance: str
    ) -> ConverseResult:
        if self.provider is None:
            return await self.reactive.converse(agent, percept, utterance)
        memories, history = self._assemble_context(agent)
        prompt = build_prompt(
            personality=agent.personality,
            memories=memories,
            history=history,
            utterance=utterance,
        )
        text = await self.provider.generate(prompt, system=self._system_prompt(agent))
        return ConverseResult(text=text.strip())

    @staticmethod
    def _assemble_context(agent: Agent) -> tuple[list[str], list[tuple[str, str]]]:
        """Gather recalled memories and conversation history from the agent, if it
        carries them. Duck-typed so memory/dialogue can be attached independently."""
        memories: list[str] = []
        memory = getattr(agent, "memory", None)
        if memory is not None and hasattr(memory, "recall"):
            memories = [item.text for item in memory.recall()]
        history: list[tuple[str, str]] = []
        conversation = getattr(agent, "conversation", None)
        if conversation is not None and hasattr(conversation, "turns"):
            history = [(turn.speaker, turn.text) for turn in conversation.turns]
        return memories, history

    @staticmethod
    def _system_prompt(agent: Agent) -> str:
        name = agent.name or "an NPC"
        return f"You are {name}, a character in a 3D world. Speak in character, briefly."
