from __future__ import annotations

from synk.schedule import Schedule, time_of_day


def test_time_of_day_phases() -> None:
    assert time_of_day(0.0, day_length=60) == "morning"
    assert time_of_day(20.0, day_length=60) == "day"
    assert time_of_day(35.0, day_length=60) == "evening"
    assert time_of_day(50.0, day_length=60) == "night"
    assert time_of_day(60.0, day_length=60) == "morning"  # wraps


def test_schedule_goal_for() -> None:
    s = Schedule({"day": "serve drinks", "night": "lock up"})
    assert s.goal_for("day") == "serve drinks"
    assert s.goal_for("morning") is None
