from __future__ import annotations

from synk.brains.base import Emote, Face, Idle, MoveTo, Wander
from synk.geometry import Vec3


def test_simple_action_kinds() -> None:
    assert Idle.kind == "idle"
    assert Wander.kind == "wander"
    assert MoveTo.kind == "move_to"
    assert Face.kind == "face"
    assert Emote.kind == "emote"


def test_actions_carry_payload() -> None:
    mt = MoveTo(target=Vec3(1, 0, 2))
    assert mt.target == Vec3(1, 0, 2)
    assert Face(target_id="npc1").target_id == "npc1"
    assert Emote(emote="wave").emote == "wave"


def test_actions_are_immutable() -> None:
    import dataclasses

    e = Emote(emote="bow")
    try:
        e.emote = "wave"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:  # pragma: no cover
        raise AssertionError("actions should be immutable")
