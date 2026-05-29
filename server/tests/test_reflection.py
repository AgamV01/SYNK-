from __future__ import annotations

import asyncio
import inspect

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


def test_reflect_is_a_coroutine_function() -> None:
    # Off-tick by construction: it's awaitable, so the sim runs it as a background task.
    assert inspect.iscoroutinefunction(reflect)


async def test_reflect_runs_concurrently_off_tick() -> None:
    stores = []
    for i in range(3):
        m = MemoryStore()
        m.add(MemoryItem(f"event {i}", ts=1.0, salience=1.0))
        stores.append(m)
    # Several agents reflecting at once, gathered off the tick path.
    results = await asyncio.gather(*(reflect(m, now=2.0) for m in stores))
    assert all(r is not None for r in results)
    assert all(len(m) == 2 for m in stores)


async def test_scheduler_gates_reflection() -> None:
    sched = ReflectionScheduler(interval=10.0)
    mem = MemoryStore()
    mem.add(MemoryItem("a thing happened", ts=0.0, salience=1.0))
    sched.due("npc1", now=0.0)  # schedule
    # Not due yet -> the sim would not reflect.
    assert sched.due("npc1", now=5.0) is False
    # Due -> reflect off-tick and mark.
    assert sched.due("npc1", now=10.0) is True
    item = await reflect(mem, now=10.0)
    sched.mark("npc1", now=10.0)
    assert item is not None
    assert sched.due("npc1", now=15.0) is False
