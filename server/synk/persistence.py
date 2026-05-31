"""SQLite persistence. Async and batched so the simulation tick never blocks on
disk: writes are queued and flushed by a background task, not awaited on the tick."""

from __future__ import annotations

import json

import aiosqlite

from .geometry import Vec3
from .dialogue import Conversation, Turn
from .memory import MemoryItem, MemoryStore
from .pathfinding import Obstacle
from .relationships import Relationships
from .schedule import Schedule
from .world import Agent, Entity, Player, World

SCHEMA = """
CREATE TABLE IF NOT EXISTS world_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS entities (
    id             TEXT PRIMARY KEY,
    kind           TEXT NOT NULL,
    name           TEXT,
    x              REAL NOT NULL,
    y              REAL NOT NULL,
    z              REAL NOT NULL,
    facing         REAL,
    zone           TEXT NOT NULL,
    current_action TEXT,
    goal           TEXT
);
CREATE TABLE IF NOT EXISTS memories (
    agent_id TEXT NOT NULL,
    text     TEXT NOT NULL,
    ts       REAL NOT NULL,
    salience REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memories_agent ON memories(agent_id);
CREATE TABLE IF NOT EXISTS relationships (
    agent_id TEXT NOT NULL,
    other_id TEXT NOT NULL,
    score    REAL NOT NULL,
    PRIMARY KEY (agent_id, other_id)
);
CREATE TABLE IF NOT EXISTS conversations (
    id           TEXT PRIMARY KEY,
    participants TEXT NOT NULL,
    turns        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS schedules (
    agent_id TEXT PRIMARY KEY,
    by_phase TEXT NOT NULL
);
"""


class Persistence:
    """Owns the SQLite connection and schema."""

    def __init__(self, path: str = ":memory:") -> None:
        self.path = path
        self._db: aiosqlite.Connection | None = None
        self._queue: list[tuple[str, tuple]] = []

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Persistence is not connected; call connect() first")
        return self._db

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(self.path)
        await self.migrate()

    async def migrate(self) -> None:
        await self.db.executescript(SCHEMA)
        await self.db.commit()

    def enqueue(self, sql: str, params: tuple = ()) -> None:
        """Queue a write. Synchronous and cheap — safe to call from the tick path.
        The actual disk write happens later in `flush`, off the tick."""
        self._queue.append((sql, params))

    @property
    def pending(self) -> int:
        return len(self._queue)

    async def flush(self) -> int:
        """Execute all queued writes in one transaction. Returns the number written."""
        if not self._queue:
            return 0
        batch = self._queue
        self._queue = []
        for sql, params in batch:
            await self.db.execute(sql, params)
        await self.db.commit()
        return len(batch)

    def save_world(self, world) -> None:
        """Queue a full snapshot of the world (meta + all entities). Synchronous and
        tick-safe; call flush() off-tick to persist. Entities are upserted by id."""
        self.enqueue(
            "INSERT OR REPLACE INTO world_meta(key, value) VALUES ('tick', ?)",
            (str(world.tick),),
        )
        self.enqueue(
            "INSERT OR REPLACE INTO world_meta(key, value) VALUES ('sim_time', ?)",
            (str(world.sim_time),),
        )
        for entity in world.all():
            self.enqueue(
                "INSERT OR REPLACE INTO entities"
                "(id, kind, name, x, y, z, facing, zone, current_action, goal) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    entity.id,
                    type(entity).__name__.lower(),
                    getattr(entity, "name", None),
                    entity.position.x,
                    entity.position.y,
                    entity.position.z,
                    getattr(entity, "facing", None),
                    entity.zone,
                    getattr(entity, "current_action", None),
                    getattr(entity, "goal", None),
                ),
            )

    def save_memory(self, agent_id: str, memory: MemoryStore) -> None:
        """Queue a replace of all memories for an agent. Tick-safe; flush off-tick."""
        self.enqueue("DELETE FROM memories WHERE agent_id = ?", (agent_id,))
        for item in memory.items:
            self.enqueue(
                "INSERT INTO memories(agent_id, text, ts, salience) VALUES (?,?,?,?)",
                (agent_id, item.text, item.ts, item.salience),
            )

    async def load_memory(self, agent_id: str, capacity: int = 100) -> MemoryStore:
        """Rebuild an agent's MemoryStore from the database (oldest-first)."""
        store = MemoryStore(capacity=capacity)
        cursor = await self.db.execute(
            "SELECT text, ts, salience FROM memories WHERE agent_id = ? ORDER BY ts",
            (agent_id,),
        )
        for text, ts, salience in await cursor.fetchall():
            store.add(MemoryItem(text=text, ts=ts, salience=salience))
        return store

    def save_relationships(self, agent_id: str, relationships: Relationships) -> None:
        """Queue a replace of an agent's sentiment scores. Tick-safe; flush off-tick."""
        self.enqueue("DELETE FROM relationships WHERE agent_id = ?", (agent_id,))
        for other_id, score in relationships.as_dict().items():
            self.enqueue(
                "INSERT INTO relationships(agent_id, other_id, score) VALUES (?,?,?)",
                (agent_id, other_id, score),
            )

    async def load_relationships(self, agent_id: str) -> Relationships:
        """Rebuild an agent's Relationships (sentiment toward others) from the database."""
        cursor = await self.db.execute(
            "SELECT other_id, score FROM relationships WHERE agent_id = ?", (agent_id,)
        )
        scores = {other_id: score for other_id, score in await cursor.fetchall()}
        return Relationships.from_scores(scores)

    def save_conversations(self, dialogue) -> None:
        """Queue a replace of all conversations (participants + turns as JSON). Tick-safe;
        flush off-tick. So dialogue history survives a restart and the LLM keeps context."""
        for convo in dialogue.all():
            participants = json.dumps(list(convo.participants))
            turns = json.dumps([[t.speaker, t.text, t.ts] for t in convo.turns])
            self.enqueue(
                "INSERT OR REPLACE INTO conversations(id, participants, turns) VALUES (?,?,?)",
                (convo.id, participants, turns),
            )

    async def load_conversations(self) -> list[Conversation]:
        """Rebuild all persisted conversations (oldest turns first within each)."""
        cursor = await self.db.execute("SELECT id, participants, turns FROM conversations")
        out: list[Conversation] = []
        for cid, participants, turns in await cursor.fetchall():
            convo = Conversation(id=cid, participants=list(json.loads(participants)))
            for speaker, text, ts in json.loads(turns):
                convo.turns.append(Turn(speaker=speaker, text=text, ts=ts))
            out.append(convo)
        return out

    def save_schedules(self, schedules: dict[str, Schedule]) -> None:
        """Queue a replace of each agent's daily schedule (phase->goal as JSON), so
        routines (including runtime overrides) survive a restart. Tick-safe."""
        for agent_id, schedule in schedules.items():
            self.enqueue(
                "INSERT OR REPLACE INTO schedules(agent_id, by_phase) VALUES (?,?)",
                (agent_id, json.dumps(schedule.by_phase)),
            )

    async def load_schedules(self) -> dict[str, Schedule]:
        """Rebuild all persisted per-agent schedules."""
        cursor = await self.db.execute("SELECT agent_id, by_phase FROM schedules")
        return {
            agent_id: Schedule(json.loads(by_phase))
            for agent_id, by_phase in await cursor.fetchall()
        }

    def save_obstacles(self, obstacles: list[Obstacle]) -> None:
        """Queue the zone's static obstacles (as JSON in world_meta) so A* navigation
        survives a restart. Tick-safe; flushed off-tick."""
        payload = json.dumps([[o.center.x, o.center.z, o.radius] for o in obstacles])
        self.enqueue(
            "INSERT OR REPLACE INTO world_meta(key, value) VALUES ('obstacles', ?)",
            (payload,),
        )

    async def load_obstacles(self) -> list[Obstacle]:
        """Reload obstacles persisted by save_obstacles (empty list if none)."""
        cursor = await self.db.execute("SELECT value FROM world_meta WHERE key = 'obstacles'")
        row = await cursor.fetchone()
        if row is None:
            return []
        return [Obstacle(center=Vec3(x, 0.0, z), radius=r) for x, z, r in json.loads(row[0])]

    async def load_into(self, world: World) -> int:
        """Load persisted entities + meta INTO an existing world (mutating it), so
        references held by the simulation/server stay valid. Returns the entity count."""
        cursor = await self.db.execute(
            "SELECT id, kind, name, x, y, z, facing, zone, current_action, goal FROM entities"
        )
        rows = await cursor.fetchall()
        for row in rows:
            id_, kind, name, x, y, z, facing, zone, current_action, goal = row
            pos = Vec3(x, y, z)
            entity: Entity
            if kind == "player":
                entity = Player(
                    id=id_, position=pos, zone=zone, name=name or "", facing=facing or 0.0
                )
            elif kind == "agent":
                entity = Agent(
                    id=id_,
                    position=pos,
                    zone=zone,
                    name=name or "",
                    facing=facing or 0.0,
                    current_action=current_action or "idle",
                    goal=goal,
                )
            else:
                entity = Entity(id=id_, position=pos, zone=zone)
            if entity.id not in world:
                world.add(entity)
        cursor = await self.db.execute("SELECT key, value FROM world_meta")
        meta = {key: value for key, value in await cursor.fetchall()}
        world.tick = int(meta.get("tick", 0))
        world.sim_time = float(meta.get("sim_time", 0.0))
        return len(rows)

    async def load_world(self) -> World:
        """Reconstruct a fresh World from the database (entities + meta). The inverse
        of save_world; used on boot so the world survives restarts."""
        world = World()
        await self.load_into(world)
        return world

    async def table_names(self) -> set[str]:
        cursor = await self.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        rows = await cursor.fetchall()
        return {row[0] for row in rows}

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None
