from __future__ import annotations

from synk.geometry import Vec3
import pytest

from synk.world import Agent, Entity, Player, World, WorldEvent


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


def test_world_add_and_len() -> None:
    w = World()
    assert len(w) == 0
    w.add(Entity(id="e1"))
    assert len(w) == 1
    assert "e1" in w


def test_world_add_duplicate_raises() -> None:
    w = World()
    w.add(Entity(id="e1"))
    with pytest.raises(ValueError):
        w.add(Entity(id="e1"))


def test_world_remove() -> None:
    w = World()
    e = Entity(id="e1")
    w.add(e)
    removed = w.remove("e1")
    assert removed is e
    assert "e1" not in w


def test_world_remove_missing_raises() -> None:
    w = World()
    with pytest.raises(KeyError):
        w.remove("ghost")


def test_world_get_and_try_get() -> None:
    w = World()
    e = Entity(id="e1")
    w.add(e)
    assert w.get("e1") is e
    assert w.try_get("e1") is e
    assert w.try_get("ghost") is None
    with pytest.raises(KeyError):
        w.get("ghost")


def test_world_by_zone() -> None:
    w = World()
    w.add(Entity(id="a", zone="tavern"))
    w.add(Entity(id="b", zone="tavern"))
    w.add(Entity(id="c", zone="market"))
    tavern_ids = {e.id for e in w.by_zone("tavern")}
    assert tavern_ids == {"a", "b"}
    assert len(w.all()) == 3
    assert w.by_zone("empty") == []


def test_within_radius_xz_and_zone_scoped() -> None:
    w = World()
    w.add(Entity(id="near", position=Vec3(3, 0, 4), zone="tavern"))  # dist 5
    w.add(Entity(id="far", position=Vec3(20, 0, 0), zone="tavern"))
    w.add(Entity(id="tall", position=Vec3(3, 100, 4), zone="tavern"))  # xz dist 5
    w.add(Entity(id="other_zone", position=Vec3(1, 0, 1), zone="market"))
    hits = {e.id for e in w.within_radius(Vec3(0, 0, 0), 5.0, zone="tavern")}
    assert hits == {"near", "tall"}  # boundary inclusive, height ignored, zone scoped


def test_within_radius_excludes_self() -> None:
    w = World()
    w.add(Entity(id="me", position=Vec3(0, 0, 0), zone="tavern"))
    w.add(Entity(id="you", position=Vec3(1, 0, 0), zone="tavern"))
    hits = {e.id for e in w.within_radius(Vec3(0, 0, 0), 10.0, "tavern", exclude_id="me")}
    assert hits == {"you"}


def test_event_buffer_is_bounded_with_monotonic_cursor() -> None:
    w = World(max_events=3)
    for i in range(5):
        w.emit_event(WorldEvent(kind="spoke", source_id=f"s{i}", zone="z", tick=i))
    # Only the last 3 are retained, but the cursor counts all 5 emitted.
    assert len(w._events) == 3
    assert w.event_count == 5
    # events_from honors the global cursor; the dropped events (0,1) are gone.
    tail = w.events_from(4)
    assert [e.source_id for e in tail] == ["s4"]
    assert [e.source_id for e in w.events_from(2)] == ["s2", "s3", "s4"]
    # Asking before the retained window returns the whole retained window, not a crash.
    assert len(w.events_from(0)) == 3


def test_world_rejects_bad_max_events() -> None:
    with pytest.raises(ValueError):
        World(max_events=0)


def test_world_clock_starts_at_zero() -> None:
    w = World()
    assert w.tick == 0
    assert w.sim_time == 0.0


def test_world_advance() -> None:
    w = World()
    w.advance(0.1)
    w.advance(0.1)
    assert w.tick == 2
    assert w.sim_time == pytest.approx(0.2)


def test_world_advance_rejects_negative_dt() -> None:
    w = World()
    with pytest.raises(ValueError):
        w.advance(-1.0)

