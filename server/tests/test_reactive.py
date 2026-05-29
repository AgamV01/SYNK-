from __future__ import annotations

from synk.brains.base import Face, Idle, MoveTo, Wander
from synk.brains.reactive import ReactiveBrain
from synk.geometry import Vec3
from synk.pathfinding import Grid
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


def test_steers_around_wall_using_path() -> None:
    # Wall at column 3 rows 0..5, gap at row 6. Agent left of wall, player right.
    grid = Grid(0, 0, 7, 7, 1.0)
    for row in range(6):
        grid.block((3, row))
    brain = ReactiveBrain(grid=grid)
    agent = Agent(id="npc1", position=grid.cell_center((0, 3)))
    player = Player(id="p1", position=grid.cell_center((6, 3)))
    action = brain.decide(agent, _percept(agent, nearby=[player]))
    assert isinstance(action, MoveTo)
    # The steering waypoint must be a real, unblocked cell center...
    cell = grid.world_to_cell(action.target)
    assert not grid.is_blocked(cell)
    # ...and it must NOT head straight at the player (that path is walled off).
    assert action.target != player.position


def test_faces_player_when_within_arrive_radius() -> None:
    brain = ReactiveBrain(arrive_radius=1.5)
    agent = Agent(id="npc1", position=Vec3(0, 0, 0))
    player = Player(id="p1", position=Vec3(1.0, 0, 0))  # within 1.5
    action = brain.decide(agent, _percept(agent, nearby=[player]))
    assert isinstance(action, Face)
    assert action.target_id == "p1"


def test_moves_when_player_outside_arrive_radius() -> None:
    brain = ReactiveBrain(arrive_radius=1.5)
    agent = Agent(id="npc1", position=Vec3(0, 0, 0))
    player = Player(id="p1", position=Vec3(5.0, 0, 0))  # beyond 1.5
    assert isinstance(brain.decide(agent, _percept(agent, nearby=[player])), MoveTo)


async def test_converse_greets_by_name_and_echoes() -> None:
    brain = ReactiveBrain()
    agent = Agent(id="npc1", name="Gus", personality="a gruff barkeep")
    result = await brain.converse(agent, _percept(agent), "hello there")
    assert "Gus" in result.text
    assert "hello there" in result.text
    assert "gruff barkeep" in result.text
    assert result.action is None


async def test_converse_handles_empty_utterance() -> None:
    brain = ReactiveBrain()
    agent = Agent(id="npc1", name="Gus")
    result = await brain.converse(agent, _percept(agent), "   ")
    assert "Gus" in result.text
    assert "What brings you here?" in result.text

