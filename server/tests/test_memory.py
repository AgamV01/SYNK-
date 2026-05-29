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


def test_decay_reduces_salience() -> None:
    s = MemoryStore()
    s.add(MemoryItem("x", ts=0.0, salience=4.0))
    s.decay(dt=1.0, rate=0.5, floor=0.0)
    assert s.items[0].salience < 4.0
    assert s.items[0].salience > 0.0


def test_decay_forgets_below_floor() -> None:
    s = MemoryStore()
    s.add(MemoryItem("faint", ts=0.0, salience=0.1))
    s.add(MemoryItem("strong", ts=0.0, salience=10.0))
    # factor = exp(-2) ~= 0.135: faint -> 0.0135 (< floor), strong -> 1.35 (kept)
    s.decay(dt=1.0, rate=2.0, floor=0.05)
    texts = {m.text for m in s.items}
    assert "faint" not in texts
    assert "strong" in texts


def test_decay_rejects_negative_dt() -> None:
    s = MemoryStore()
    with pytest.raises(ValueError):
        s.decay(dt=-1.0)


def test_recall_recent_newest_first() -> None:
    s = MemoryStore()
    s.add(MemoryItem("old", ts=1.0))
    s.add(MemoryItem("mid", ts=2.0))
    s.add(MemoryItem("new", ts=3.0))
    recent = s.recall_recent(2)
    assert [m.text for m in recent] == ["new", "mid"]


def test_recall_recent_nonpositive_is_empty() -> None:
    s = MemoryStore()
    s.add(MemoryItem("x", ts=1.0))
    assert s.recall_recent(0) == []


def test_recall_salient_most_important_first() -> None:
    s = MemoryStore()
    s.add(MemoryItem("trivial", ts=3.0, salience=0.5))
    s.add(MemoryItem("vital", ts=1.0, salience=9.0))
    s.add(MemoryItem("notable", ts=2.0, salience=4.0))
    top = s.recall_salient(2)
    assert [m.text for m in top] == ["vital", "notable"]


def test_recall_salient_nonpositive_is_empty() -> None:
    s = MemoryStore()
    s.add(MemoryItem("x", ts=1.0, salience=5.0))
    assert s.recall_salient(0) == []


def test_recall_union_dedupes_and_orders() -> None:
    s = MemoryStore()
    # An old-but-salient memory and several recent low-salience ones.
    s.add(MemoryItem("ancient_vital", ts=1.0, salience=100.0))
    s.add(MemoryItem("r1", ts=10.0, salience=1.0))
    s.add(MemoryItem("r2", ts=11.0, salience=1.0))
    s.add(MemoryItem("r3", ts=12.0, salience=1.0))
    out = s.recall(recent_n=2, salient_k=1)
    texts = [m.text for m in out]
    # union = {r3, r2} (recent) ∪ {ancient_vital} (salient)
    assert set(texts) == {"r3", "r2", "ancient_vital"}
    # no duplicates
    assert len(texts) == len(set(texts))
    # newest-first ordering by ts
    assert texts == ["r3", "r2", "ancient_vital"]


def test_recall_union_no_duplicate_when_recent_is_salient() -> None:
    s = MemoryStore()
    item = MemoryItem("both", ts=5.0, salience=9.0)
    s.add(item)
    s.add(MemoryItem("other", ts=4.0, salience=1.0))
    out = s.recall(recent_n=5, salient_k=5)
    assert [m.text for m in out].count("both") == 1

