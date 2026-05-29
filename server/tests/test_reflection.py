from __future__ import annotations

import pytest

from synk.memory import MemoryItem, MemoryStore
from synk.reflection import ReflectionScheduler, reflect


def test_scheduler_rejects_bad_interval() -> None:
    with pytest.raises(ValueError):
        ReflectionScheduler(0)


def test_first_call_schedules_but_is_not_due() -> None:
    s = ReflectionScheduler(interval=10.0)
    assert s.due("a", now=0.0) is False
    assert s.due("a", now=9.9) is False
    assert s.due("a", now=10.0) is True


def test_mark_resets_next_due() -> None:
    s = ReflectionScheduler(interval=10.0)
    s.due("a", now=0.0)
    assert s.due("a", now=10.0) is True
    s.mark("a", now=10.0)
    assert s.due("a", now=19.0) is False
    assert s.due("a", now=20.0) is True


def test_independent_per_agent() -> None:
    s = ReflectionScheduler(interval=5.0)
    s.due("a", now=0.0)
    s.due("b", now=2.0)
    assert s.due("a", now=5.0) is True
    assert s.due("b", now=5.0) is False
    assert s.due("b", now=7.0) is True


async def test_reflect_summarizes_into_salient_memory() -> None:
    mem = MemoryStore()
    mem.add(MemoryItem("met a traveler", ts=1.0, salience=1.0))
    mem.add(MemoryItem("served some ale", ts=2.0, salience=2.0))
    item = await reflect(mem, now=3.0, provider=None)
    assert item is not None
    assert "traveler" in item.text and "ale" in item.text
    assert item.salience > 2.0  # stickier than its constituents
    assert item in mem.items


async def test_reflect_empty_memory_returns_none() -> None:
    assert await reflect(MemoryStore(), now=1.0, provider=None) is None
