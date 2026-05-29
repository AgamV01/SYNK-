from __future__ import annotations

from fastapi.testclient import TestClient

from synk.brains.reactive import ReactiveBrain
from synk.geometry import Vec3
from synk.server import Throttle, broadcast_world_state, create_app
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
        pid = ws.receive_json()["player_id"]
        ws.send_json({"type": "move", "v": 1, "position": [1.0, 0.0, 2.0], "facing": 1.5})
        # A second join forces in-order processing; receiving its welcome guarantees
        # the move above was already handled.
        ws.send_json({"type": "join", "v": 1, "name": "sync"})
        ws.receive_json()
        player = app.state.world.get(pid)
        assert player.position == Vec3(1.0, 0.0, 2.0)
        assert player.facing == 1.5


def test_ws_say_returns_dialogue() -> None:
    app = create_app()
    app.state.world.add(Agent(id="npc_gus", name="Gus", zone="tavern", personality="a barkeep"))
    app.state.sim.register("npc_gus", ReactiveBrain())
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join", "v": 1, "name": "Ada", "zone": "tavern"})
        ws.receive_json()  # welcome
        ws.send_json({"type": "say", "v": 1, "target": "npc_gus", "text": "hello"})
        reply = ws.receive_json()
        assert reply["type"] == "dialogue"
        assert reply["agent_id"] == "npc_gus"
        assert "Gus" in reply["text"]
        assert "hello" in reply["text"]
        assert reply["overheard"] is False


def test_ws_interact_returns_agent_event() -> None:
    app = create_app()
    app.state.world.add(Agent(id="npc_gus", name="Gus", zone="tavern"))
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join", "v": 1, "name": "Ada", "zone": "tavern"})
        ws.receive_json()  # welcome
        ws.send_json(
            {"type": "interact", "v": 1, "target": "npc_gus", "kind": "give_item", "payload": {"item": "coin"}}
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
        pid = ws.receive_json()["player_id"]
        assert pid in app.state.world
        ws.send_json({"type": "leave", "v": 1})
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
        ws.receive_json()  # welcome
        ws.send_json({"type": "say", "v": 1, "target": "ghost", "text": "hi"})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "unknown_agent"


def test_ws_unknown_message_returns_error() -> None:
    client = TestClient(create_app())
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join", "v": 1, "name": "Ada"})
        ws.receive_json()  # welcome
        ws.send_json({"type": "frobnicate", "v": 1})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "bad_message"
