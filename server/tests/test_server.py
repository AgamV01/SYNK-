from __future__ import annotations

from fastapi.testclient import TestClient

from synk.geometry import Vec3
from synk.server import create_app


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
