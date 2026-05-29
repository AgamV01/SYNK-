from __future__ import annotations

from synk.memory import MemoryItem


def test_memory_item_fields() -> None:
    m = MemoryItem(text="player gave me a coin", ts=12.5, salience=3.0)
    assert m.text == "player gave me a coin"
    assert m.ts == 12.5
    assert m.salience == 3.0


def test_memory_item_default_salience() -> None:
    m = MemoryItem(text="saw a stranger", ts=1.0)
    assert m.salience == 1.0
