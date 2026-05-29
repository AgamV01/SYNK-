from __future__ import annotations

import pytest

from synk.brains.base import (
    Emote,
    Face,
    GiveItem,
    Handoff,
    MoveTo,
    SetGoal,
    action_from_dict,
)
from synk.geometry import Vec3


def test_action_from_dict_move_to() -> None:
    a = action_from_dict({"type": "move_to", "target": [1, 0, 2]})
    assert isinstance(a, MoveTo)
    assert a.target == Vec3(1, 0, 2)


def test_action_from_dict_all_kinds() -> None:
    assert isinstance(action_from_dict({"type": "face", "target_id": "p1"}), Face)
    assert isinstance(action_from_dict({"type": "emote", "emote": "wave"}), Emote)
    assert isinstance(
        action_from_dict({"type": "give_item", "item": "ale", "to": "p1"}), GiveItem
    )
    assert isinstance(action_from_dict({"type": "set_goal", "goal": "rest"}), SetGoal)
    assert isinstance(
        action_from_dict({"type": "handoff", "to": "g1", "topic": "coin"}), Handoff
    )


def test_action_from_dict_unknown_type_raises() -> None:
    with pytest.raises(ValueError):
        action_from_dict({"type": "teleport"})


def test_action_from_dict_missing_field_raises() -> None:
    with pytest.raises(ValueError):
        action_from_dict({"type": "emote"})  # missing 'emote'
