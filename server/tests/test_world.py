from __future__ import annotations

from synk.geometry import Vec3
from synk.world import Agent, Entity, Player


def test_entity_defaults() -> None:
    e = Entity(id="e1")
    assert e.id == "e1"
    assert e.position == Vec3(0, 0, 0)
    assert e.zone == "default"


def test_entity_explicit_fields() -> None:
    e = Entity(id="e2", position=Vec3(1, 0, 2), zone="tavern")
    assert e.position == Vec3(1, 0, 2)
    assert e.zone == "tavern"


def test_entity_position_is_mutable() -> None:
    e = Entity(id="e3")
    e.position = Vec3(5, 0, 5)
    assert e.position == Vec3(5, 0, 5)


def test_player_is_entity() -> None:
    p = Player(id="p1", name="Ada", zone="tavern", facing=1.5)
    assert isinstance(p, Entity)
    assert p.name == "Ada"
    assert p.facing == 1.5


def test_agent_skeleton_defaults() -> None:
    a = Agent(id="npc1", name="Gus", personality="gruff barkeep")
    assert isinstance(a, Entity)
    assert a.current_action == "idle"
    assert a.goal is None
    assert a.personality == "gruff barkeep"

