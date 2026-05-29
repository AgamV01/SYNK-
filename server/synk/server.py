"""FastAPI WebSocket server implementing the SYNK protocol (protocol/messages.md).

Clients send intents (join/move/say/interact/leave); the server is authoritative and
streams welcome/world_state/agent_event/dialogue/error back."""

from __future__ import annotations

import asyncio
import os
import secrets
import time
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import actions
from .auth import AuthManager
from .brains.llm import LLMBrain
from .brains.providers import select_provider
from .brains.reactive import ReactiveBrain
from .dialogue import DialogueManager
from .geometry import Vec3
from .memory import MemoryItem, MemoryStore, score_event_salience
from .pathfinding import Grid, Obstacle
from .perception import perceive
from .persistence import Persistence
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


class RateLimiter:
    """Token-bucket rate limiter (per connection). `allow()` returns False when the
    caller is sending faster than `rate` msgs/sec sustained (with `burst` headroom)."""

    def __init__(self, rate: float, burst: float, clock: Callable[[], float] | None = None) -> None:
        self.rate = rate
        self.burst = burst
        self._clock = clock or time.monotonic
        self._tokens = float(burst)
        self._last = self._clock()

    def allow(self) -> bool:
        now = self._clock()
        self._tokens = min(self.burst, self._tokens + (now - self._last) * self.rate)
        self._last = now
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False


def _env_allowed_origins() -> list[str]:
    raw = os.environ.get("ALLOWED_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip()]


def origin_allowed(origin: str | None, allowed: list[str]) -> bool:
    """Allow if no allowlist is configured (dev), if the request has no Origin
    (non-browser clients), or if the Origin is explicitly allowed."""
    if not allowed or origin is None:
        return True
    return origin in allowed


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


async def broadcast_events(
    world: World,
    connections: Mapping[str, object],
    since_index: int,
) -> int:
    """Stream new WorldEvents to clients since `since_index`. `spoke` events become
    `dialogue` messages; everything else becomes `agent_event`. Zone-scoped. Returns
    the new cursor (world.event_count) to pass back next call."""
    for event in world.events_from(since_index):
        if event.kind == "spoke":
            msg = {
                "type": "dialogue",
                "v": PROTOCOL_VERSION,
                "agent_id": event.source_id,
                "text": event.payload.get("text", ""),
                "overheard": event.payload.get("overheard", False),
            }
        else:
            msg = {
                "type": "agent_event",
                "v": PROTOCOL_VERSION,
                "agent_id": event.source_id,
                "kind": event.kind,
                "payload": event.payload,
            }
        for player_id, ws in list(connections.items()):
            player = world.try_get(player_id)
            if player is not None and player.zone == event.zone:
                await ws.send_json(msg)
    return world.event_count


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


def populate_demo(world: World, sim: Simulation) -> None:
    """Add the tavern demo world: three personality NPCs around two obstacles, each
    with a reactive brain registered on the simulation. Lets `uvicorn synk.server:app`
    show living NPCs with zero configuration."""
    obstacles = [Obstacle(center=Vec3(-4, 0, -2), radius=1.2), Obstacle(center=Vec3(5, 0, 1), radius=1.0)]
    grid = Grid.from_obstacles(-15, -15, 30, 30, 1.0, obstacles)
    npcs = [
        Agent(id="npc_gus", name="Gus", personality="a gruff barkeep", position=Vec3(0, 0, -3), zone="tavern"),
        Agent(id="npc_mira", name="Mira", personality="a curious bard", position=Vec3(3, 0, 2), zone="tavern"),
        Agent(id="npc_tomas", name="Tomas", personality="a suspicious guard", position=Vec3(-3, 0, 3), zone="tavern"),
    ]
    provider = select_provider()  # Mock with no key; real LLM when ANTHROPIC/OPENAI key is set
    for npc in npcs:
        npc.memory = MemoryStore()  # episodic memory (duck-typed; used by LLMBrain + reflection)
        world.add(npc)
        reactive = ReactiveBrain(grid=grid, arrive_radius=1.5)  # cheap tick layer keeps the grid
        sim.register(npc.id, LLMBrain(provider=provider, reactive=reactive))


async def _attach_brains_and_memory(world: World, sim: Simulation, persistence: Persistence) -> None:
    """For agents restored from the DB, reload their memory and register a brain so the
    simulation drives them again after a restart."""
    provider = select_provider()
    for entity in world.all():
        if isinstance(entity, Agent) and entity.id not in sim.brains:
            entity.memory = await persistence.load_memory(entity.id)
            sim.register(entity.id, LLMBrain(provider=provider, reactive=ReactiveBrain()))


def create_app(
    demo: bool = False,
    allowed_origins: list[str] | None = None,
    msg_rate: float = 50.0,
    msg_burst: float = 100.0,
    db_path: str | None = None,
) -> FastAPI:
    world = World()
    auth = AuthManager()
    dialogue = DialogueManager()
    db_path = db_path if db_path is not None else os.environ.get("SYNK_DB_PATH")
    persistence = Persistence(db_path) if db_path else None
    sim = Simulation(world, dt=SNAPSHOT_INTERVAL, persistence=persistence)
    connections: dict[str, WebSocket] = {}
    broadcast_throttle = Throttle(0.0)
    allowed = allowed_origins if allowed_origins is not None else _env_allowed_origins()

    # With persistence, the populate-vs-load decision happens in lifespan (after connect).
    if demo and persistence is None:
        populate_demo(world, sim)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        tasks: list[asyncio.Task] = []
        if persistence is not None:
            await persistence.connect()
            loaded = await persistence.load_into(world)
            if loaded == 0 and demo:
                populate_demo(world, sim)
            else:
                await _attach_brains_and_memory(world, sim, persistence)
        if demo or persistence is not None:
            tasks.append(asyncio.create_task(sim.run()))

            async def broadcaster() -> None:
                event_cursor = world.event_count
                while True:
                    await asyncio.sleep(sim.dt)
                    await broadcast_world_state(world, connections, broadcast_throttle)
                    event_cursor = await broadcast_events(world, connections, event_cursor)

            tasks.append(asyncio.create_task(broadcaster()))
        try:
            yield
        finally:
            sim.stop()
            for task in tasks:
                task.cancel()
            if persistence is not None:
                persistence.save_world(world)
                await persistence.flush()
                await persistence.close()

    app = FastAPI(title="SYNK", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed or ["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.world = world
    app.state.allowed_origins = allowed
    app.state.auth = auth
    app.state.dialogue = dialogue
    app.state.sim = sim
    app.state.connections = connections

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        if not origin_allowed(websocket.headers.get("origin"), allowed):
            await websocket.close(code=1008)  # policy violation
            return
        await websocket.accept()
        player_id: str | None = None
        limiter = RateLimiter(rate=msg_rate, burst=msg_burst)
        try:
            while True:
                msg = await websocket.receive_json()
                if not limiter.allow():
                    await send_error(websocket, "rate_limited", "slow down")
                    continue
                if msg.get("v") != PROTOCOL_VERSION:
                    await send_error(
                        websocket, "unsupported_version", f"unsupported protocol version {msg.get('v')!r}"
                    )
                    continue
                mtype = msg.get("type")

                if mtype == "join":
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
                    continue

                # Every other intent requires a prior join and a valid session token.
                if player_id is None:
                    await send_error(websocket, "not_joined", "send join before any intent")
                    continue
                if not auth.is_for(msg.get("token", ""), player_id):
                    await send_error(websocket, "unauthorized", "missing or invalid session token")
                    continue

                if mtype == "move":
                    player = world.try_get(player_id)
                    if isinstance(player, Player):
                        position = msg.get("position")
                        if position is not None:
                            player.position = Vec3.from_list(position)
                        facing = msg.get("facing")
                        if facing is not None:
                            player.facing = float(facing)
                elif mtype == "say":
                    target_id = msg.get("target")
                    text = msg.get("text", "")
                    agent = world.try_get(target_id) if target_id else None
                    if isinstance(agent, Agent):
                        brain = sim.brains.get(agent.id) or ReactiveBrain()
                        percept = perceive(world, agent)
                        convo = dialogue.route_player_message(player_id, agent.id, text)
                        agent.conversation = convo  # so LLMBrain sees history
                        if getattr(agent, "memory", None) is not None:
                            agent.memory.add(
                                MemoryItem(
                                    text=f"{player_id} said: {text}",
                                    ts=world.sim_time,
                                    salience=score_event_salience("spoke"),
                                )
                            )
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
                elif mtype == "interact":
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
                elif mtype == "leave":
                    break
                else:
                    await send_error(
                        websocket, "bad_message", f"unhandled message: {mtype!r}"
                    )
        except WebSocketDisconnect:
            pass
        finally:
            if player_id is not None:
                connections.pop(player_id, None)
                if player_id in world:
                    world.remove(player_id)

    return app


app = create_app(demo=True)
