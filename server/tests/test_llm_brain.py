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


def _percept(agent: Agent) -> Percept:
    return Percept(agent_id=agent.id, position=agent.position, tick=0)


def test_decide_delegates_to_reactive_without_io() -> None:
    brain = LLMBrain(provider=ExplodingProvider())
    agent = Agent(id="npc1", position=Vec3(0, 0, 0))
    # Alone + restless reactive default -> Wander, and the provider is never touched.
    assert isinstance(brain.decide(agent, _percept(agent)), Wander)
