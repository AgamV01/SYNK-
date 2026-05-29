from __future__ import annotations

from synk.persistence import Persistence


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
