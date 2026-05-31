from __future__ import annotations

import logging

import pytest

from synk.actions import apply_action
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
from synk.world import Agent, World


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


def _agent_in_world() -> tuple[World, Agent]:
    world = World()
    agent = Agent(id="npc1", zone="tavern")
    world.add(agent)
    world.advance(0.1)
    return world, agent


def test_apply_move_to_emits_moved_event() -> None:
    world, agent = _agent_in_world()
    event = apply_action(world, agent, MoveTo(target=Vec3(3, 0, 4)))
    assert event is not None
    assert event.kind == "moved"
    assert event.payload == {"to": [3.0, 0.0, 4.0]}
    assert agent.current_action == "move_to"
    assert event in world.recent_events()


def test_apply_emote_emits_emoted_event() -> None:
    world, agent = _agent_in_world()
    event = apply_action(world, agent, Emote(emote="wave"))
    assert event is not None
    assert event.kind == "emoted"
    assert event.payload == {"emote": "wave"}
    assert agent.current_action == "wave"


def test_apply_give_item() -> None:
    world, agent = _agent_in_world()
    event = apply_action(world, agent, GiveItem(item="ale", to_id="p1"))
    assert event is not None
    assert event.kind == "gave_item"
    assert event.payload == {"item": "ale", "to": "p1"}


def test_apply_set_goal_updates_agent() -> None:
    world, agent = _agent_in_world()
    event = apply_action(world, agent, SetGoal(goal="find the thief"))
    assert event is not None
    assert event.kind == "goal_changed"
    assert event.payload == {"goal": "find the thief"}
    assert agent.goal == "find the thief"


def test_apply_handoff() -> None:
    world, agent = _agent_in_world()
    event = apply_action(world, agent, Handoff(to_id="guard", topic="the coin"))
    assert event is not None
    assert event.kind == "handoff"
    assert event.payload == {"to": "guard", "topic": "the coin"}


def test_apply_unhandled_action_returns_none() -> None:
    from synk.brains.base import Idle

    world, agent = _agent_in_world()
    assert apply_action(world, agent, Idle()) is None


def test_action_tool_schemas_cover_action_vocabulary() -> None:
    # A3: tool schemas are derived from ACTION_SCHEMA — one tool per action with required fields.
    from synk.brains.base import ACTION_SCHEMA, action_tool_schemas

    schemas = action_tool_schemas()
    by_name = {t["name"]: t for t in schemas}
    assert set(by_name) == set(ACTION_SCHEMA)
    move = by_name["move_to"]
    assert move["input_schema"]["required"] == ["target"]
    assert "target" in move["input_schema"]["properties"]
    assert move["description"]  # non-empty human-readable description


def test_tool_call_to_output_roundtrips_through_parser() -> None:
    # A3: a serialized tool-call parses back into a typed Action with the speech preserved.
    from synk.brains.base import tool_call_to_output

    out = tool_call_to_output("give_item", {"item": "coin", "to": "player_1"}, speech="Here.")
    speech, action = parse_llm_output(out)
    assert speech == "Here."
    assert isinstance(action, GiveItem)
    assert action.item == "coin"
    assert action.to_id == "player_1"
