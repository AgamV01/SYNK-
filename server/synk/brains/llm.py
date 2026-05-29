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
        prompt = build_prompt(
            personality=agent.personality,
            memories=[],
            history=[],
            utterance=utterance,
        )
        text = await self.provider.generate(prompt, system=self._system_prompt(agent))
        return ConverseResult(text=text.strip())

    @staticmethod
    def _system_prompt(agent: Agent) -> str:
        name = agent.name or "an NPC"
        return f"You are {name}, a character in a 3D world. Speak in character, briefly."
