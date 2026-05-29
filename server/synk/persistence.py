"""SQLite persistence. Async and batched so the simulation tick never blocks on
disk: writes are queued and flushed by a background task, not awaited on the tick."""

from __future__ import annotations

import aiosqlite

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
"""


class Persistence:
    """Owns the SQLite connection and schema."""

    def __init__(self, path: str = ":memory:") -> None:
        self.path = path
        self._db: aiosqlite.Connection | None = None

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
