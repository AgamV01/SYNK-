from __future__ import annotations

from synk.dialogue import Conversation, DialogueManager, Turn


def test_add_turn_records_history_and_participants() -> None:
    c = Conversation(id="c1")
    c.add_turn("player_1", "hello", ts=1.0)
    c.add_turn("npc_gus", "well met", ts=2.0)
    c.add_turn("player_1", "what's on tap?", ts=3.0)
    assert len(c.turns) == 3
    assert c.participants == ["player_1", "npc_gus"]
    assert isinstance(c.turns[0], Turn)
    assert c.turns[1].speaker == "npc_gus"


def test_history_limit() -> None:
    c = Conversation(id="c1")
    for i in range(5):
        c.add_turn("player_1", f"msg {i}", ts=float(i))
    assert [t.text for t in c.history(limit=2)] == ["msg 3", "msg 4"]
    assert len(c.history()) == 5
    assert c.history(limit=0) == []


def test_manager_routes_player_message() -> None:
    dm = DialogueManager()
    convo = dm.route_player_message("player_1", "npc_gus", "hello", ts=1.0)
    assert convo.participants == ["player_1", "npc_gus"]
    assert convo.turns[-1].speaker == "player_1"
    assert convo.turns[-1].text == "hello"


def test_manager_reuses_conversation_per_pair() -> None:
    dm = DialogueManager()
    a = dm.start("player_1", "npc_gus")
    b = dm.start("player_1", "npc_gus")
    assert a is b
    c = dm.start("player_1", "npc_bo")
    assert c is not a
