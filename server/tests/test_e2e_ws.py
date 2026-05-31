from __future__ import annotations

from fastapi.testclient import TestClient

import asyncio

from synk.brains.llm import LLMBrain
from synk.brains.reactive import ReactiveBrain
from synk.dialogue import DialogueManager
from synk.geometry import Vec3
from synk.server import broadcast_events, create_app
from synk.simulation import Simulation
from synk.world import Agent, Player, World


class _LineProvider:
    name = "line"

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        return "Quiet night, isn't it?"


class _FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, msg: dict) -> None:
        self.sent.append(msg)


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
        token = welcome["token"]

        # move -> authoritative position update (token-authenticated).
        ws.send_json({"type": "move", "v": 1, "position": [2.0, 0.0, 0.0], "facing": 0.0, "token": token})

        # say -> dialogue. Receiving this proves the prior move was processed (in-order).
        ws.send_json({"type": "say", "v": 1, "target": "npc_gus", "text": "good evening", "token": token})
        dialogue = ws.receive_json()
        assert dialogue["type"] == "dialogue"
        assert dialogue["agent_id"] == "npc_gus"
        assert "Gus" in dialogue["text"]
        assert "good evening" in dialogue["text"]

        # The move landed before the say was handled.
        assert app.state.world.get(player_id).position == Vec3(2.0, 0.0, 0.0)


async def test_e2e_autonomous_npc_dialogue_reaches_client() -> None:
    """End-to-end across the full pipeline (deterministic, no wall-clock): two LLM NPCs
    converse autonomously; their off-tick speech drains to world events and is delivered to
    a connected client via broadcast_events as overheard dialogue — no player action."""
    world = World()
    world.add(Agent(id="a", name="A", position=Vec3(0, 0, 0), zone="room"))
    world.add(Agent(id="b", name="B", position=Vec3(1, 0, 0), zone="room"))
    world.add(Player(id="p", zone="room"))  # a bystanding client in the zone
    sim = Simulation(
        world, dt=0.1, dialogue=DialogueManager(),
        npc_chat=True, npc_chat_turns=2, npc_chat_interval=0.0,
        deliberate_threshold=100.0,  # isolate NPC-chat speech
    )
    sim.register("a", LLMBrain(provider=_LineProvider()))
    sim.register("b", LLMBrain(provider=_LineProvider()))

    conns = {"p": _FakeWS()}
    cursor = world.event_count
    for _ in range(8):
        sim.step()
        if sim._pending:
            await asyncio.gather(*sim._pending)
        cursor = await broadcast_events(world, conns, cursor)

    dialogues = [m for m in conns["p"].sent if m["type"] == "dialogue"]
    assert dialogues, "client should receive autonomous NPC dialogue over the live pipeline"
    assert dialogues[0]["overheard"] is True
    assert dialogues[0]["text"] == "Quiet night, isn't it?"
