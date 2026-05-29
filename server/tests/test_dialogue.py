from __future__ import annotations

from synk.dialogue import (
    NEARBY_RADIUS,
    Conversation,
    DialogueManager,
    Turn,
    overhearers,
)
from synk.geometry import Vec3
from synk.world import Agent, Player, World


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


def test_manager_append_reply_and_fetch_history() -> None:
    dm = DialogueManager()
    dm.route_player_message("player_1", "npc_gus", "hello", ts=1.0)
    dm.append_agent_reply("player_1", "npc_gus", "well met", ts=2.0)
    hist = dm.history("player_1", "npc_gus")
    assert [(t.speaker, t.text) for t in hist] == [
        ("player_1", "hello"),
        ("npc_gus", "well met"),
    ]


def test_manager_history_unknown_pair_is_empty() -> None:
    dm = DialogueManager()
    assert dm.history("nobody", "noone") == []


def test_multiparty_npc_conversation() -> None:
    dm = DialogueManager()
    dm.group("tavern_chat", ["npc_gus", "npc_bo"])
    dm.route_group_message("tavern_chat", "npc_gus", "quiet night, eh?", ts=1.0)
    dm.route_group_message("tavern_chat", "npc_bo", "aye, too quiet", ts=2.0)
    convo = dm.group("tavern_chat")
    assert set(convo.participants) == {"npc_gus", "npc_bo"}
    assert [t.speaker for t in convo.turns] == ["npc_gus", "npc_bo"]
    assert convo.turns[1].text == "aye, too quiet"


def test_overhearers_nearby_players_excluding_addressed() -> None:
    world = World()
    gus = Agent(id="npc_gus", position=Vec3(0, 0, 0), zone="tavern")
    addressed = Player(id="p1", position=Vec3(1, 0, 0), zone="tavern")
    bystander = Player(id="p2", position=Vec3(3, 0, 0), zone="tavern")
    far = Player(id="p3", position=Vec3(50, 0, 0), zone="tavern")
    other_zone = Player(id="p4", position=Vec3(1, 0, 0), zone="market")
    for e in (gus, addressed, bystander, far, other_zone):
        world.add(e)
    heard = {p.id for p in overhearers(world, gus, exclude_id="p1")}
    assert heard == {"p2"}  # not addressed p1, not far p3, not other-zone p4, not self


def test_overhearers_default_radius() -> None:
    assert NEARBY_RADIUS == 12.0
