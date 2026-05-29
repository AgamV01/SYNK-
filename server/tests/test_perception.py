from __future__ import annotations

from synk.geometry import Vec3
from synk.perception import Percept
from synk.world import Entity, WorldEvent


def test_percept_defaults_empty() -> None:
    p = Percept(agent_id="npc1", position=Vec3(0, 0, 0), tick=5)
    assert p.nearby == []
    assert p.events == []
    assert p.tick == 5


def test_percept_holds_entities_and_events() -> None:
    other = Entity(id="e2", position=Vec3(1, 0, 1), zone="tavern")
    ev = WorldEvent(kind="spoke", source_id="e2", zone="tavern", tick=5)
    p = Percept(
        agent_id="npc1",
        position=Vec3(0, 0, 0),
        tick=5,
        nearby=[other],
        events=[ev],
    )
    assert p.nearby[0].id == "e2"
    assert p.events[0].kind == "spoke"
