from __future__ import annotations

from synk.brains.base import Idle, Wander
from synk.brains.reactive import ReactiveBrain
from synk.geometry import Vec3
from synk.perception import Percept
from synk.world import Agent


def _percept(agent: Agent, nearby=None, events=None) -> Percept:
    return Percept(
        agent_id=agent.id,
        position=agent.position,
        tick=0,
        nearby=list(nearby or []),
        events=list(events or []),
    )


def test_restless_brain_wanders_when_alone() -> None:
    brain = ReactiveBrain(restless=True)
    agent = Agent(id="npc1", position=Vec3(0, 0, 0))
    assert isinstance(brain.decide(agent, _percept(agent)), Wander)


def test_calm_brain_idles_when_alone() -> None:
    brain = ReactiveBrain(restless=False)
    agent = Agent(id="npc1", position=Vec3(0, 0, 0))
    assert isinstance(brain.decide(agent, _percept(agent)), Idle)
