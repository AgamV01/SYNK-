from __future__ import annotations

import pytest

from synk.memory import (
    DEFAULT_SALIENCE,
    MemoryItem,
    MemoryStore,
    score_event_salience,
)


def test_memory_item_fields() -> None:
    m = MemoryItem(text="player gave me a coin", ts=12.5, salience=3.0)
    assert m.text == "player gave me a coin"
    assert m.ts == 12.5
    assert m.salience == 3.0


def test_memory_item_default_salience() -> None:
    m = MemoryItem(text="saw a stranger", ts=1.0)
    assert m.salience == 1.0


def test_store_rejects_bad_capacity() -> None:
    with pytest.raises(ValueError):
        MemoryStore(capacity=0)


def test_store_add_and_len() -> None:
    s = MemoryStore(capacity=10)
    s.add(MemoryItem("a", ts=1.0))
    s.add(MemoryItem("b", ts=2.0))
    assert len(s) == 2
    assert {m.text for m in s.items} == {"a", "b"}


def test_store_evicts_least_salient_when_full() -> None:
    s = MemoryStore(capacity=3)
    s.add(MemoryItem("low", ts=1.0, salience=0.5))
    s.add(MemoryItem("mid", ts=2.0, salience=2.0))
    s.add(MemoryItem("high", ts=3.0, salience=5.0))
    s.add(MemoryItem("new", ts=4.0, salience=1.0))  # over capacity
    texts = {m.text for m in s.items}
    assert len(s) == 3
    assert "low" not in texts  # least salient evicted
    assert {"mid", "high", "new"} == texts


def test_salience_known_kinds_ordered() -> None:
    assert score_event_salience("gave_item") > score_event_salience("spoke")
    assert score_event_salience("spoke") > score_event_salience("moved")


def test_salience_unknown_kind_is_default() -> None:
    assert score_event_salience("teleported") == DEFAULT_SALIENCE

