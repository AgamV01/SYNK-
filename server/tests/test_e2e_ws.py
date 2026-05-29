from __future__ import annotations

from fastapi.testclient import TestClient

from synk.brains.reactive import ReactiveBrain
from synk.geometry import Vec3
from synk.server import create_app
from synk.world import Agent


def test_e2e_join_move_say() -> None:
    """Full client flow over one socket: join -> welcome (with world state snapshot),
    move (applied authoritatively), say -> dialogue reply."""
    app = create_app()
    app.state.world.add(
        Agent(id="npc_gus", name="Gus", position=Vec3(0, 0, 0), zone="tavern", personality="a gruff barkeep")
    )
    app.state.sim.register("npc_gus", ReactiveBrain())
    client = TestClient(app)

    with client.websocket_connect("/ws") as ws:
        # join -> welcome, which carries the zone's world state snapshot.
        ws.send_json({"type": "join", "v": 1, "name": "Ada", "zone": "tavern"})
        welcome = ws.receive_json()
        assert welcome["type"] == "welcome"
        assert welcome["zone"] == "tavern"
        agent_ids = {a["id"] for a in welcome["snapshot"]["agents"]}
        assert "npc_gus" in agent_ids  # state: the agent is in the snapshot
        player_id = welcome["player_id"]

        # move -> authoritative position update.
        ws.send_json({"type": "move", "v": 1, "position": [2.0, 0.0, 0.0], "facing": 0.0})

        # say -> dialogue. Receiving this proves the prior move was processed (in-order).
        ws.send_json({"type": "say", "v": 1, "target": "npc_gus", "text": "good evening"})
        dialogue = ws.receive_json()
        assert dialogue["type"] == "dialogue"
        assert dialogue["agent_id"] == "npc_gus"
        assert "Gus" in dialogue["text"]
        assert "good evening" in dialogue["text"]

        # The move landed before the say was handled.
        assert app.state.world.get(player_id).position == Vec3(2.0, 0.0, 0.0)
