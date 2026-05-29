"""FastAPI WebSocket server implementing the SYNK protocol (protocol/messages.md).

Clients send intents (join/move/say/interact/leave); the server is authoritative and
streams welcome/world_state/agent_event/dialogue/error back."""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable, Mapping

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from . import actions
from .auth import AuthManager
from .brains.reactive import ReactiveBrain
from .dialogue import DialogueManager
from .geometry import Vec3
from .perception import perceive
from .simulation import Simulation
from .world import Agent, Player, World

PROTOCOL_VERSION = 1
DEFAULT_ZONE = "default"
SNAPSHOT_INTERVAL = 0.1  # 10 Hz, per protocol/messages.md


class Throttle:
    """Rate gate: ready() returns True at most once per `interval` seconds."""

    def __init__(self, interval: float, clock: Callable[[], float] | None = None) -> None:
        self.interval = interval
        self._clock = clock or time.monotonic
        self._last: float | None = None

    def ready(self) -> bool:
        now = self._clock()
        if self._last is None or now - self._last >= self.interval:
            self._last = now
            return True
        return False


async def broadcast_world_state(
    world: World,
    connections: Mapping[str, object],
    throttle: Throttle,
) -> int:
    """Send each connected player a per-zone world_state snapshot, throttled. Returns
    the number of clients sent to (0 if throttled). Scoped to each player's zone."""
    if not throttle.ready():
        return 0
    sent = 0
    for player_id, ws in list(connections.items()):
        player = world.try_get(player_id)
        zone = player.zone if player is not None else DEFAULT_ZONE
        snap = zone_snapshot(world, zone)
        await ws.send_json(
            {
                "type": "world_state",
                "v": PROTOCOL_VERSION,
                "zone": zone,
                "tick": snap["tick"],
                "agents": snap["agents"],
            }
        )
        sent += 1
    return sent


def zone_snapshot(world: World, zone: str) -> dict:
    """A world_state-style snapshot of the agents in a zone."""
    agents = [
        {
            "id": e.id,
            "name": e.name,
            "position": e.position.to_list(),
            "facing": e.facing,
            "action": e.current_action,
        }
        for e in world.by_zone(zone)
        if isinstance(e, Agent)
    ]
    return {"tick": world.tick, "agents": agents}


async def send_error(ws: object, code: str, message: str) -> None:
    await ws.send_json(
        {"type": "error", "v": PROTOCOL_VERSION, "code": code, "message": message}
    )


def create_app() -> FastAPI:
    app = FastAPI(title="SYNK")
    world = World()
    auth = AuthManager()
    dialogue = DialogueManager()
    sim = Simulation(world)
    connections: dict[str, WebSocket] = {}

    app.state.world = world
    app.state.auth = auth
    app.state.dialogue = dialogue
    app.state.sim = sim
    app.state.connections = connections

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        await websocket.accept()
        player_id: str | None = None
        try:
            while True:
                msg = await websocket.receive_json()
                if msg.get("type") == "join":
                    name = msg.get("name", "anon")
                    zone = msg.get("zone") or DEFAULT_ZONE
                    player_id = f"player_{secrets.token_hex(4)}"
                    session = auth.issue(player_id)
                    world.add(Player(id=player_id, name=name, zone=zone))
                    connections[player_id] = websocket
                    await websocket.send_json(
                        {
                            "type": "welcome",
                            "v": PROTOCOL_VERSION,
                            "player_id": player_id,
                            "token": session.token,
                            "tick_rate": round(1 / sim.dt),
                            "zone": zone,
                            "snapshot": zone_snapshot(world, zone),
                        }
                    )
                elif msg.get("type") == "move" and player_id is not None:
                    player = world.try_get(player_id)
                    if isinstance(player, Player):
                        position = msg.get("position")
                        if position is not None:
                            player.position = Vec3.from_list(position)
                        facing = msg.get("facing")
                        if facing is not None:
                            player.facing = float(facing)
                elif msg.get("type") == "say" and player_id is not None:
                    target_id = msg.get("target")
                    text = msg.get("text", "")
                    agent = world.try_get(target_id) if target_id else None
                    if isinstance(agent, Agent):
                        brain = sim.brains.get(agent.id) or ReactiveBrain()
                        percept = perceive(world, agent)
                        dialogue.route_player_message(player_id, agent.id, text)
                        # Deliberative reply: off the sim tick, so awaiting is fine here.
                        result = await brain.converse(agent, percept, text)
                        dialogue.append_agent_reply(player_id, agent.id, result.text)
                        await websocket.send_json(
                            {
                                "type": "dialogue",
                                "v": PROTOCOL_VERSION,
                                "agent_id": agent.id,
                                "text": result.text,
                                "overheard": False,
                            }
                        )
                        if result.action is not None:
                            actions.apply_action(world, agent, result.action)
                    else:
                        await send_error(
                            websocket, "unknown_agent", f"no agent {target_id!r}"
                        )
                elif msg.get("type") == "interact" and player_id is not None:
                    target_id = msg.get("target")
                    kind = msg.get("kind", "")
                    agent = world.try_get(target_id) if target_id else None
                    if isinstance(agent, Agent):
                        # The agent acknowledges the interaction with a nod.
                        await websocket.send_json(
                            {
                                "type": "agent_event",
                                "v": PROTOCOL_VERSION,
                                "agent_id": agent.id,
                                "kind": "emoted",
                                "payload": {"emote": "nod", "in_response_to": kind},
                            }
                        )
                    else:
                        await send_error(
                            websocket, "unknown_agent", f"no agent {target_id!r}"
                        )
                elif msg.get("type") == "leave":
                    break
                else:
                    await send_error(
                        websocket, "bad_message", f"unhandled message: {msg.get('type')!r}"
                    )
        except WebSocketDisconnect:
            pass
        finally:
            if player_id is not None:
                connections.pop(player_id, None)
                if player_id in world:
                    world.remove(player_id)

    return app


app = create_app()
