from __future__ import annotations

from synk.dialogue import Conversation, Turn


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
