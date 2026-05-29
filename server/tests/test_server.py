from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from synk.brains.reactive import ReactiveBrain
from synk.geometry import Vec3
from synk.memory import MemoryStore
from synk.server import (
    RateLimiter,
    Throttle,
    broadcast_world_state,
    create_app,
    origin_allowed,
)
from synk.world import Agent, Player, World


def test_healthz() -> None:
    client = TestClient(create_app())
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ws_join_returns_welcome_with_token() -> None:
    client = TestClient(create_app())
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join", "v": 1, "name": "Ada", "zone": "tavern"})
        welcome = ws.receive_json()
        assert welcome["type"] == "welcome"
        assert welcome["v"] == 1
        assert welcome["player_id"].startswith("player_")
        assert welcome["token"]
        assert welcome["zone"] == "tavern"
        assert welcome["tick_rate"] == 10
        assert "snapshot" in welcome and "agents" in welcome["snapshot"]


def test_ws_join_default_zone() -> None:
    client = TestClient(create_app())
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join", "v": 1, "name": "Bo"})
        welcome = ws.receive_json()
        assert welcome["zone"] == "default"


def test_ws_move_updates_player() -> None:
    app = create_app()
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join", "v": 1, "name": "Ada", "zone": "tavern"})
        welcome = ws.receive_json()
        pid, token = welcome["player_id"], welcome["token"]
        ws.send_json({"type": "move", "v": 1, "position": [1.0, 0.0, 2.0], "facing": 1.5, "token": token})
        # A second join forces in-order processing; receiving its welcome guarantees
        # the move above was already handled.
        ws.send_json({"type": "join", "v": 1, "name": "sync"})
        ws.receive_json()
        player = app.state.world.get(pid)
        assert player.position == Vec3(1.0, 0.0, 2.0)
        assert player.facing == 1.5


def test_ws_move_without_token_is_unauthorized() -> None:
    app = create_app()
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join", "v": 1, "name": "Ada", "zone": "tavern"})
        pid = ws.receive_json()["player_id"]
        ws.send_json({"type": "move", "v": 1, "position": [9.0, 0.0, 9.0]})  # no token
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "unauthorized"
        assert app.state.world.get(pid).position == Vec3(0, 0, 0)  # unchanged


def test_ws_forged_token_is_unauthorized() -> None:
    app = create_app()
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join", "v": 1, "name": "Ada", "zone": "tavern"})
        ws.receive_json()
        ws.send_json({"type": "move", "v": 1, "position": [9.0, 0.0, 9.0], "token": "forged"})
        err = ws.receive_json()
        assert err["code"] == "unauthorized"


def test_ws_say_returns_dialogue() -> None:
    app = create_app()
    app.state.world.add(Agent(id="npc_gus", name="Gus", zone="tavern", personality="a barkeep"))
    app.state.sim.register("npc_gus", ReactiveBrain())
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join", "v": 1, "name": "Ada", "zone": "tavern"})
        token = ws.receive_json()["token"]
        ws.send_json({"type": "say", "v": 1, "target": "npc_gus", "text": "hello", "token": token})
        reply = ws.receive_json()
        assert reply["type"] == "dialogue"
        assert reply["agent_id"] == "npc_gus"
        assert "Gus" in reply["text"]
        assert "hello" in reply["text"]
        assert reply["overheard"] is False


def test_ws_say_records_memory_and_conversation() -> None:
    app = create_app()
    gus = Agent(id="npc_gus", name="Gus", zone="tavern", personality="a barkeep")
    gus.memory = MemoryStore()
    app.state.world.add(gus)
    app.state.sim.register("npc_gus", ReactiveBrain())
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join", "v": 1, "name": "Ada", "zone": "tavern"})
        token = ws.receive_json()["token"]
        ws.send_json({"type": "say", "v": 1, "target": "npc_gus", "text": "I am Ada the brave", "token": token})
        ws.receive_json()  # dialogue reply
    assert any("I am Ada the brave" in m.text for m in gus.memory.items)
    assert gus.conversation is not None
    turns = [t.text for t in gus.conversation.turns]
    assert "I am Ada the brave" in turns  # player turn recorded
    assert len(turns) >= 2  # + agent reply


def test_ws_interact_returns_agent_event() -> None:
    app = create_app()
    app.state.world.add(Agent(id="npc_gus", name="Gus", zone="tavern"))
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join", "v": 1, "name": "Ada", "zone": "tavern"})
        token = ws.receive_json()["token"]
        ws.send_json(
            {"type": "interact", "v": 1, "target": "npc_gus", "kind": "give_item", "payload": {"item": "coin"}, "token": token}
        )
        event = ws.receive_json()
        assert event["type"] == "agent_event"
        assert event["agent_id"] == "npc_gus"
        assert event["kind"] == "emoted"
        assert event["payload"]["in_response_to"] == "give_item"


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, msg: dict) -> None:
        self.sent.append(msg)


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


async def test_broadcast_world_state_is_zone_scoped() -> None:
    world = World()
    world.add(Agent(id="gus", name="Gus", position=Vec3(0, 0, 0), zone="tavern"))
    world.add(Agent(id="bo", name="Bo", position=Vec3(1, 0, 0), zone="market"))
    world.add(Player(id="p_tavern", zone="tavern"))
    world.add(Player(id="p_market", zone="market"))
    world.advance(0.1)
    conns = {"p_tavern": FakeWS(), "p_market": FakeWS()}
    sent = await broadcast_world_state(world, conns, Throttle(0.1))
    assert sent == 2
    tavern_msg = conns["p_tavern"].sent[0]
    assert tavern_msg["type"] == "world_state"
    assert tavern_msg["zone"] == "tavern"
    assert tavern_msg["tick"] == 1
    assert {a["id"] for a in tavern_msg["agents"]} == {"gus"}  # only tavern agents
    assert {a["id"] for a in conns["p_market"].sent[0]["agents"]} == {"bo"}


async def test_broadcast_is_throttled() -> None:
    world = World()
    world.add(Player(id="p1", zone="default"))
    conns = {"p1": FakeWS()}
    clock = FakeClock()
    throttle = Throttle(0.1, clock=clock)
    assert await broadcast_world_state(world, conns, throttle) == 1
    clock.t = 0.05  # too soon
    assert await broadcast_world_state(world, conns, throttle) == 0
    clock.t = 0.15  # past the interval
    assert await broadcast_world_state(world, conns, throttle) == 1
    assert len(conns["p1"].sent) == 2


def test_ws_leave_cleans_up() -> None:
    app = create_app()
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join", "v": 1, "name": "Ada"})
        welcome = ws.receive_json()
        pid = welcome["player_id"]
        assert pid in app.state.world
        ws.send_json({"type": "leave", "v": 1, "token": welcome["token"]})
    # After leave the server removes the player and its connection.
    assert pid not in app.state.world
    assert pid not in app.state.connections


def test_ws_disconnect_cleans_up() -> None:
    app = create_app()
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join", "v": 1, "name": "Ada"})
        pid = ws.receive_json()["player_id"]
    # Abrupt close (no leave) also cleans up.
    assert pid not in app.state.world
    assert pid not in app.state.connections


def test_ws_say_unknown_agent_returns_error() -> None:
    client = TestClient(create_app())
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join", "v": 1, "name": "Ada"})
        token = ws.receive_json()["token"]
        ws.send_json({"type": "say", "v": 1, "target": "ghost", "text": "hi", "token": token})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "unknown_agent"


def test_rate_limiter_burst_then_blocks_then_refills() -> None:
    clock = FakeClock()
    rl = RateLimiter(rate=10.0, burst=3.0, clock=clock)
    assert rl.allow() and rl.allow() and rl.allow()  # 3-token burst
    assert rl.allow() is False  # exhausted
    clock.t = 0.1  # +0.1s * 10/s = 1 token
    assert rl.allow() is True
    assert rl.allow() is False


def test_origin_allowed_rules() -> None:
    assert origin_allowed(None, []) is True  # no allowlist -> open (dev)
    assert origin_allowed("http://evil.com", []) is True
    assert origin_allowed(None, ["http://good.com"]) is True  # non-browser, no Origin
    assert origin_allowed("http://good.com", ["http://good.com"]) is True
    assert origin_allowed("http://evil.com", ["http://good.com"]) is False


def test_ws_rejects_disallowed_origin() -> None:
    client = TestClient(create_app(allowed_origins=["http://good.com"]))
    with pytest.raises(Exception):  # server closes (1008) before accept
        with client.websocket_connect("/ws", headers={"origin": "http://evil.com"}) as ws:
            ws.receive_json()


def test_ws_allows_listed_origin() -> None:
    client = TestClient(create_app(allowed_origins=["http://good.com"]))
    with client.websocket_connect("/ws", headers={"origin": "http://good.com"}) as ws:
        ws.send_json({"type": "join", "v": 1, "name": "Ada"})
        assert ws.receive_json()["type"] == "welcome"


def test_ws_rate_limited_error() -> None:
    # burst of 1 so the second message in the same tick is rate-limited.
    app = create_app(msg_rate=0.0, msg_burst=1.0)
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join", "v": 1, "name": "Ada"})
        assert ws.receive_json()["type"] == "welcome"  # consumes the 1 token
        ws.send_json({"type": "move", "v": 1, "position": [1, 0, 1]})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "rate_limited"


def test_ws_unsupported_version_returns_error() -> None:
    client = TestClient(create_app())
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join", "v": 2, "name": "Ada"})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "unsupported_version"


def test_ws_unknown_message_returns_error() -> None:
    client = TestClient(create_app())
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join", "v": 1, "name": "Ada"})
        token = ws.receive_json()["token"]
        ws.send_json({"type": "frobnicate", "v": 1, "token": token})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "bad_message"
