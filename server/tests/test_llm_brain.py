from __future__ import annotations

from synk.brains.base import Wander
from synk.brains.llm import LLMBrain
from synk.geometry import Vec3
from synk.perception import Percept
from synk.world import Agent


class ExplodingProvider:
    """Fails loudly if anyone calls it — used to prove decide() does no I/O."""

    name = "exploding"

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        raise AssertionError("provider must never be called from decide()")


class StubProvider:
    name = "stub"

    def __init__(self) -> None:
        self.last_prompt: str | None = None

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        self.last_prompt = prompt
        return "  A stubbed line of dialogue.  "


def _percept(agent: Agent) -> Percept:
    return Percept(agent_id=agent.id, position=agent.position, tick=0)


def test_decide_delegates_to_reactive_without_io() -> None:
    brain = LLMBrain(provider=ExplodingProvider())
    agent = Agent(id="npc1", position=Vec3(0, 0, 0))
    # Alone + restless reactive default -> Wander, and the provider is never touched.
    assert isinstance(brain.decide(agent, _percept(agent)), Wander)


async def test_converse_uses_provider_when_present() -> None:
    provider = StubProvider()
    brain = LLMBrain(provider=provider)
    agent = Agent(id="npc1", name="Gus", personality="a gruff barkeep")
    result = await brain.converse(agent, _percept(agent), "what's on tap?")
    assert result.text == "A stubbed line of dialogue."  # provider output, trimmed
    assert provider.last_prompt is not None
    assert "what's on tap?" in provider.last_prompt


async def test_converse_degrades_to_reactive_without_provider() -> None:
    brain = LLMBrain(provider=None)  # zero-key path
    agent = Agent(id="npc1", name="Gus", personality="a gruff barkeep")
    result = await brain.converse(agent, _percept(agent), "hello there")
    # Falls back to the reactive templated greeting.
    assert "Gus" in result.text
    assert "hello there" in result.text
