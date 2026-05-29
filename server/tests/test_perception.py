from __future__ import annotations

from synk.geometry import Vec3
from synk.perception import Percept, perceive
from synk.world import Entity, World, WorldEvent


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


def test_perceive_within_sense_radius() -> None:
    w = World()
    me = Entity(id="me", position=Vec3(0, 0, 0), zone="tavern")
    w.add(me)
    w.add(Entity(id="close", position=Vec3(2, 0, 0), zone="tavern"))
    w.add(Entity(id="edge", position=Vec3(5, 0, 0), zone="tavern"))
    w.add(Entity(id="beyond", position=Vec3(7, 0, 0), zone="tavern"))
    w.advance(0.1)
    p = perceive(w, me, sense_radius=5.0)
    assert p.agent_id == "me"
    assert p.tick == 1
    assert {e.id for e in p.nearby} == {"close", "edge"}  # self excluded, beyond excluded


def test_perceive_excludes_other_zones() -> None:
    w = World()
    me = Entity(id="me", position=Vec3(0, 0, 0), zone="tavern")
    w.add(me)
    w.add(Entity(id="same_zone", position=Vec3(1, 0, 0), zone="tavern"))
    # Physically adjacent but in a different logical zone — must not be perceived.
    w.add(Entity(id="other_zone", position=Vec3(1, 0, 0), zone="market"))
    p = perceive(w, me, sense_radius=50.0)
    assert {e.id for e in p.nearby} == {"same_zone"}

