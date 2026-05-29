from __future__ import annotations

import logging

import pytest

from synk.brains.base import (
    Emote,
    Face,
    GiveItem,
    Handoff,
    MoveTo,
    SetGoal,
    action_from_dict,
    parse_llm_output,
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


def test_parse_speech_with_action() -> None:
    speech, action = parse_llm_output(
        '{"speech": "Here, take this.", "action": {"type": "give_item", "item": "ale", "to": "p1"}}'
    )
    assert speech == "Here, take this."
    assert isinstance(action, GiveItem)
    assert action.item == "ale"


def test_parse_speech_only() -> None:
    speech, action = parse_llm_output('{"speech": "Just chatting."}')
    assert speech == "Just chatting."
    assert action is None


def test_parse_json_embedded_in_prose() -> None:
    raw = 'Sure! ```json\n{"speech": "Off I go.", "action": {"type": "move_to", "target": [3, 0, 4]}}\n```'
    speech, action = parse_llm_output(raw)
    assert speech == "Off I go."
    assert isinstance(action, MoveTo)
    assert action.target == Vec3(3, 0, 4)


def test_malformed_action_falls_back_to_speech_only(caplog) -> None:
    with caplog.at_level(logging.WARNING, logger="synk.brains"):
        speech, action = parse_llm_output(
            '{"speech": "I would, but...", "action": {"type": "teleport"}}'
        )
    assert speech == "I would, but..."
    assert action is None  # bad action dropped
    assert any("malformed" in r.message.lower() for r in caplog.records)


def test_non_json_text_is_speech_only_no_raise() -> None:
    speech, action = parse_llm_output("Just an ordinary sentence, no JSON here.")
    assert speech == "Just an ordinary sentence, no JSON here."
    assert action is None


def test_garbage_braces_do_not_raise() -> None:
    speech, action = parse_llm_output("here is some {not valid json at all")
    assert action is None
    assert "here is some" in speech
