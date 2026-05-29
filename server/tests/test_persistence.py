from __future__ import annotations

from synk.geometry import Vec3
from synk.memory import MemoryItem, MemoryStore
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


async def test_save_then_load_world_on_boot(tmp_path) -> None:
    db_path = str(tmp_path / "synk.db")
    world = World()
    world.add(Agent(id="npc1", name="Gus", position=Vec3(1, 0, 2), zone="tavern", goal="serve"))
    world.add(Player(id="p1", name="Ada", position=Vec3(3, 0, 4), zone="tavern"))
    for _ in range(7):
        world.advance(0.1)

    writer = Persistence(db_path)
    await writer.connect()
    writer.save_world(world)
    await writer.flush()
    await writer.close()

    # Fresh process / connection.
    booted = Persistence(db_path)
    await booted.connect()
    try:
        loaded = await booted.load_world()
        assert loaded.tick == 7
        npc = loaded.get("npc1")
        assert isinstance(npc, Agent)
        assert npc.name == "Gus" and npc.goal == "serve"
        assert npc.position == Vec3(1, 0, 2)
        assert isinstance(loaded.get("p1"), Player)
    finally:
        await booted.close()


async def test_memory_roundtrip(tmp_path) -> None:
    db_path = str(tmp_path / "mem.db")
    mem = MemoryStore()
    mem.add(MemoryItem("met a traveler", ts=1.0, salience=2.0))
    mem.add(MemoryItem("a brawl broke out", ts=2.0, salience=5.0))

    writer = Persistence(db_path)
    await writer.connect()
    writer.save_memory("npc1", mem)
    await writer.flush()
    await writer.close()

    booted = Persistence(db_path)
    await booted.connect()
    try:
        loaded = await booted.load_memory("npc1")
        pairs = {(m.text, m.salience) for m in loaded.items}
        assert pairs == {("met a traveler", 2.0), ("a brawl broke out", 5.0)}
        assert await booted.load_memory("unknown") is not None
        assert len(await booted.load_memory("unknown")) == 0
    finally:
        await booted.close()


async def test_save_memory_replaces_prior(tmp_path) -> None:
    db_path = str(tmp_path / "mem2.db")
    p = Persistence(db_path)
    await p.connect()
    try:
        first = MemoryStore()
        first.add(MemoryItem("old", ts=1.0, salience=1.0))
        p.save_memory("npc1", first)
        await p.flush()
        second = MemoryStore()
        second.add(MemoryItem("new", ts=2.0, salience=1.0))
        p.save_memory("npc1", second)
        await p.flush()
        loaded = await p.load_memory("npc1")
        assert [m.text for m in loaded.items] == ["new"]  # replaced, not appended
    finally:
        await p.close()
