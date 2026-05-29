from __future__ import annotations

from synk.geometry import Vec3
from synk.world import Entity


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
