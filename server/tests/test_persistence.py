from __future__ import annotations

from synk.geometry import Vec3
from synk.persistence import Persistence
from synk.world import Agent, Player, World


async def test_migrate_creates_tables() -> None:
    p = Persistence(":memory:")
    await p.connect()
    try:
        tables = await p.table_names()
        assert {"world_meta", "entities", "memories"} <= tables
    finally:
        await p.close()


async def test_migrate_is_idempotent() -> None:
    p = Persistence(":memory:")
    await p.connect()
    try:
        await p.migrate()  # running again must not raise
        tables = await p.table_names()
        assert "entities" in tables
    finally:
        await p.close()


def test_db_property_requires_connect() -> None:
    import pytest

    p = Persistence(":memory:")
    with pytest.raises(RuntimeError):
        _ = p.db


async def test_enqueue_is_synchronous_and_flush_writes() -> None:
    p = Persistence(":memory:")
    await p.connect()
    try:
        p.enqueue(
            "INSERT INTO memories(agent_id, text, ts, salience) VALUES (?,?,?,?)",
            ("npc1", "remembered a face", 1.0, 2.0),
        )
        p.enqueue(
            "INSERT INTO memories(agent_id, text, ts, salience) VALUES (?,?,?,?)",
            ("npc1", "served ale", 2.0, 1.0),
        )
        assert p.pending == 2  # not yet written
        written = await p.flush()
        assert written == 2
        assert p.pending == 0
        cursor = await p.db.execute("SELECT COUNT(*) FROM memories")
        (count,) = await cursor.fetchone()
        assert count == 2
    finally:
        await p.close()


async def test_flush_empty_queue_returns_zero() -> None:
    p = Persistence(":memory:")
    await p.connect()
    try:
        assert await p.flush() == 0
    finally:
        await p.close()


async def test_save_world_snapshot() -> None:
    world = World()
    world.add(Agent(id="npc1", name="Gus", position=Vec3(1, 0, 2), zone="tavern", goal="serve"))
    world.add(Player(id="p1", name="Ada", position=Vec3(3, 0, 4), zone="tavern"))
    world.advance(0.1)
    p = Persistence(":memory:")
    await p.connect()
    try:
        p.save_world(world)
        await p.flush()
        cursor = await p.db.execute("SELECT id, kind, name, x, zone FROM entities ORDER BY id")
        rows = await cursor.fetchall()
        assert rows == [
            ("npc1", "agent", "Gus", 1.0, "tavern"),
            ("p1", "player", "Ada", 3.0, "tavern"),
        ]
        cursor = await p.db.execute("SELECT value FROM world_meta WHERE key='tick'")
        (tick,) = await cursor.fetchone()
        assert tick == "1"
    finally:
        await p.close()
