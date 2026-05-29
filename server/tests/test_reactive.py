from __future__ import annotations

from synk.brains.base import Idle, MoveTo, Wander
from synk.brains.reactive import ReactiveBrain
from synk.geometry import Vec3
from synk.perception import Percept
from synk.world import Agent, Player


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


def test_approaches_nearby_player() -> None:
    brain = ReactiveBrain()
    agent = Agent(id="npc1", position=Vec3(0, 0, 0))
    player = Player(id="p1", position=Vec3(8, 0, 0))
    action = brain.decide(agent, _percept(agent, nearby=[player]))
    assert isinstance(action, MoveTo)
    assert action.target == Vec3(8, 0, 0)


def test_approaches_nearest_of_several_players() -> None:
    brain = ReactiveBrain()
    agent = Agent(id="npc1", position=Vec3(0, 0, 0))
    far = Player(id="far", position=Vec3(9, 0, 0))
    near = Player(id="near", position=Vec3(2, 0, 0))
    action = brain.decide(agent, _percept(agent, nearby=[far, near]))
    assert isinstance(action, MoveTo)
    assert action.target == Vec3(2, 0, 0)
