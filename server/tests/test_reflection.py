from __future__ import annotations

import pytest

from synk.reflection import ReflectionScheduler


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
