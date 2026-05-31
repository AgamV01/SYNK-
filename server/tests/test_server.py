from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from synk.brains.reactive import ReactiveBrain
from synk.geometry import Vec3
from synk.memory import MemoryItem, MemoryStore
from synk.persistence import Persistence
from synk.server import (
    RateLimiter,
    Throttle,
    broadcast_events,
    broadcast_world_state,
    create_app,
    origin_allowed,
)
from synk.world import Agent, Player, World, WorldEvent


def test_healthz() -> None:
    client = TestClient(create_app())
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metrics_endpoint() -> None:
    client = TestClient(create_app())
    body = client.get("/metrics").json()
    assert body["v"] == 1
    for key in ("llm_calls", "deliberations", "reflections", "npc_turns", "ticks", "agents", "entities"):
        assert key in body


def test_prometheus_exposition_format() -> None:
    # E2: the formatter emits HELP/TYPE + a numeric line per metric, skips non-numerics.
    from synk.server import prometheus_exposition

    text = prometheus_exposition({"llm_calls": 5, "ticks": 12, "sim_time": 1.2, "v": "x"})
    assert "# TYPE synk_llm_calls counter" in text
    assert "synk_llm_calls 5" in text
    assert "# TYPE synk_ticks gauge" in text
    assert "synk_ticks 12" in text
    assert "synk_v" not in text  # non-numeric skipped
    assert text.endswith("\n")


def test_metrics_prom_endpoint() -> None:
    # E2: /metrics/prom scrapes as Prometheus text exposition.
    client = TestClient(create_app(demo=True))
    resp = client.get("/metrics/prom")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "synk_llm_calls" in resp.text
    assert "synk_tokens_used" in resp.text


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
        # B5: the snapshot carries the world clock + phase for the day/night cycle.
        assert welcome["snapshot"]["phase"] in {"morning", "day", "evening", "night"}
        assert "world_time" in welcome["snapshot"]


def test_zone_snapshot_includes_phase_and_world_time() -> None:
    # B5: zone_snapshot reports phase derived from the world clock + day length.
    from synk.server import zone_snapshot
    from synk.world import World

    world = World()
    world.sim_time = 0.0
    snap = zone_snapshot(world, "tavern", day_length=60.0)
    assert snap["phase"] == "morning"
    assert snap["world_time"] == 0.0
    world.sim_time = 50.0  # last quarter of a 60s day -> night
    assert zone_snapshot(world, "tavern", day_length=60.0)["phase"] == "night"


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


async def test_server_loads_persisted_world_and_memory_on_boot(tmp_path) -> None:
    db = str(tmp_path / "synk.db")
    # Seed a DB: one agent with a memory.
    seed = Persistence(db)
    await seed.connect()
    seeded_world = World()
    seeded_world.add(Agent(id="npc_seed", name="Seed", position=Vec3(2, 0, 2), zone="tavern"))
    seeded_world.advance(0.1)
    seed.save_world(seeded_world)
    mem = MemoryStore()
    mem.add(MemoryItem("i recall the storm", ts=1.0, salience=3.0))
    seed.save_memory("npc_seed", mem)
    await seed.flush()
    await seed.close()

    # Boot the app against that DB — lifespan loads the world + memory + brains.
    app = create_app(db_path=db)
    with TestClient(app):
        assert "npc_seed" in app.state.world
        agent = app.state.world.get("npc_seed")
        assert agent.name == "Seed"
        assert "npc_seed" in app.state.sim.brains  # brain re-registered
        assert any("storm" in m.text for m in agent.memory.items)  # memory restored


async def test_restored_agents_keep_grid_navigation(tmp_path) -> None:
    from synk.pathfinding import Obstacle

    db = str(tmp_path / "synk.db")
    seed = Persistence(db)
    await seed.connect()
    w = World()
    w.add(Agent(id="npc_gus", name="Gus", position=Vec3(0, 0, -3), zone="tavern"))
    w.advance(0.1)
    seed.save_world(w)
    seed.save_obstacles([Obstacle(center=Vec3(-4, 0, -2), radius=1.2)])
    await seed.flush()
    await seed.close()

    app = create_app(db_path=db)
    with TestClient(app):
        brain = app.state.sim.brains["npc_gus"]
        assert brain.reactive.grid is not None  # grid rebuilt from persisted obstacles


def test_demo_npcs_use_hybrid_llm_brain() -> None:
    from synk.brains.llm import LLMBrain

    app = create_app(demo=True)
    # populate_demo runs at create time; NPCs use the hybrid brain (reactive tick +
    # off-tick LLM converse). With no API key the provider is Mock, so it runs offline.
    assert isinstance(app.state.sim.brains["npc_gus"], LLMBrain)
    assert app.state.world.get("npc_gus").memory is not None


def test_app_boots_from_world_file(tmp_path) -> None:
    # B2: create_app(world_file=...) loads agents/brains from a YAML world file.
    from synk.brains.llm import LLMBrain
    from synk.brains.reactive import ReactiveBrain

    world_yaml = tmp_path / "mini.yaml"
    world_yaml.write_text(
        "name: mini\n"
        "agents:\n"
        "  - id: npc_ann\n"
        "    name: Ann\n"
        "    personality: a tinkerer\n"
        "    position: [1, 0, 2]\n"
        "    zone: shop\n"
        "    brain: llm\n"
        "  - id: npc_bob\n"
        "    name: Bob\n"
        "    position: [0, 0, 0]\n"
        "    zone: shop\n"
        "    brain: reactive\n",
        encoding="utf-8",
    )
    app = create_app(demo=True, world_file=str(world_yaml))
    sim = app.state.sim
    assert set(sim.brains) == {"npc_ann", "npc_bob"}
    assert isinstance(sim.brains["npc_ann"], LLMBrain)
    assert isinstance(sim.brains["npc_bob"], ReactiveBrain)
    ann = app.state.world.get("npc_ann")
    assert ann.name == "Ann" and ann.zone == "shop"


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


def test_ws_say_is_overheard_by_nearby_player() -> None:
    app = create_app()
    app.state.world.add(Agent(id="npc_gus", name="Gus", zone="tavern", position=Vec3(0, 0, 0)))
    app.state.sim.register("npc_gus", ReactiveBrain())
    client = TestClient(app)
    with client.websocket_connect("/ws") as wa, client.websocket_connect("/ws") as wb:
        wa.send_json({"type": "join", "v": 1, "name": "Ada", "zone": "tavern"})
        token_a = wa.receive_json()["token"]
        wb.send_json({"type": "join", "v": 1, "name": "Bo", "zone": "tavern"})
        wb.receive_json()  # B's welcome (both players spawn at origin, near Gus)
        wa.send_json({"type": "say", "v": 1, "target": "npc_gus", "text": "hello", "token": token_a})
        direct = wa.receive_json()
        assert direct["type"] == "dialogue" and direct["overheard"] is False
        overheard = wb.receive_json()  # B wasn't addressed but is nearby
        assert overheard["type"] == "dialogue"
        assert overheard["agent_id"] == "npc_gus"
        assert overheard["overheard"] is True


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


async def test_broadcast_events_dialogue_and_agent_event_zone_scoped() -> None:
    world = World()
    world.add(Player(id="p_in", zone="tavern"))
    world.add(Player(id="p_out", zone="market"))
    world.advance(0.1)
    world.emit_event(WorldEvent(kind="spoke", source_id="gus", zone="tavern", tick=1, payload={"text": "hello"}))
    world.emit_event(WorldEvent(kind="emoted", source_id="gus", zone="tavern", tick=1, payload={"emote": "wave"}))
    world.emit_event(WorldEvent(kind="spoke", source_id="bo", zone="market", tick=1, payload={"text": "psst"}))
    conns = {"p_in": FakeWS(), "p_out": FakeWS()}
    cursor = await broadcast_events(world, conns, 0)
    assert cursor == 3
    in_types = {m["type"] for m in conns["p_in"].sent}
    assert in_types == {"dialogue", "agent_event"}
    dlg = next(m for m in conns["p_in"].sent if m["type"] == "dialogue")
    assert dlg["text"] == "hello"
    assert [m["text"] for m in conns["p_out"].sent if m["type"] == "dialogue"] == ["psst"]
    # Cursor advances; a second call with no new events sends nothing.
    again = await broadcast_events(world, conns, cursor)
    assert again == 3
    assert len(conns["p_in"].sent) == 2  # unchanged


async def test_broadcast_builds_snapshot_once_per_zone(monkeypatch) -> None:
    import synk.server as srv

    world = World()
    world.add(Agent(id="g", name="G", zone="tavern"))
    world.add(Player(id="p1", zone="tavern"))
    world.add(Player(id="p2", zone="tavern"))  # second client in the SAME zone
    real = srv.zone_snapshot
    calls = {"n": 0}

    def counting(w, z, day_length=60.0):
        calls["n"] += 1
        return real(w, z, day_length)

    monkeypatch.setattr(srv, "zone_snapshot", counting)
    conns = {"p1": FakeWS(), "p2": FakeWS()}
    sent = await srv.broadcast_world_state(world, conns, srv.Throttle(0.0))
    assert sent == 2
    assert calls["n"] == 1  # one snapshot reused for both same-zone clients


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
