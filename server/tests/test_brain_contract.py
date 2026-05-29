from __future__ import annotations

import pytest

from synk.brains.base import (
    Brain,
    ConverseResult,
    Emote,
    Face,
    GiveItem,
    Goal,
    Handoff,
    Idle,
    MoveTo,
    SetGoal,
    Wander,
)
from synk.geometry import Vec3
from synk.perception import Percept
from synk.world import Agent


class DummyBrain:
    def decide(self, agent: Agent, percept: Percept) -> Idle:
        return Idle()

    async def converse(self, agent: Agent, percept: Percept, utterance: str) -> ConverseResult:
        return ConverseResult(text=f"You said: {utterance}", action=Emote(emote="nod"))


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


def test_deliberative_action_kinds() -> None:
    assert GiveItem.kind == "give_item"
    assert SetGoal.kind == "set_goal"
    assert Handoff.kind == "handoff"


def test_deliberative_actions_carry_payload() -> None:
    g = GiveItem(item="ale", to_id="player_1")
    assert (g.item, g.to_id) == ("ale", "player_1")
    assert SetGoal(goal="find the thief").goal == "find the thief"
    h = Handoff(to_id="npc_guard", topic="the missing coin")
    assert (h.to_id, h.topic) == ("npc_guard", "the missing coin")


def test_actions_are_immutable() -> None:
    import dataclasses

    e = Emote(emote="bow")
    try:
        e.emote = "wave"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:  # pragma: no cover
        raise AssertionError("actions should be immutable")


def test_dummy_brain_satisfies_protocol() -> None:
    assert isinstance(DummyBrain(), Brain)


def test_dummy_brain_decide_is_sync_action() -> None:
    brain = DummyBrain()
    agent = Agent(id="npc1")
    percept = Percept(agent_id="npc1", position=Vec3(0, 0, 0), tick=0)
    assert isinstance(brain.decide(agent, percept), Idle)


def test_goal_defaults_and_completion() -> None:
    g = Goal(description="find the thief")
    assert g.priority == 1.0
    assert g.done is False
    g.complete()
    assert g.done is True


def test_goal_priority_ordering() -> None:
    goals = [Goal("low", priority=1.0), Goal("high", priority=5.0), Goal("mid", priority=3.0)]
    ordered = sorted(goals, key=lambda g: g.priority, reverse=True)
    assert [g.description for g in ordered] == ["high", "mid", "low"]


async def test_dummy_brain_converse_is_async() -> None:
    brain = DummyBrain()
    agent = Agent(id="npc1")
    percept = Percept(agent_id="npc1", position=Vec3(0, 0, 0), tick=0)
    result = await brain.converse(agent, percept, "hello")
    assert result.text == "You said: hello"
    assert isinstance(result.action, Emote)
