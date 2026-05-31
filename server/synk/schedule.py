"""Daily routines: a world clock maps sim time to a phase (morning/day/evening/night),
and a per-agent Schedule maps each phase to a goal — so NPCs pursue routines on their own,
making the world feel alive without a player present."""

from __future__ import annotations

PHASES = ("morning", "day", "evening", "night")
DEFAULT_DAY_LENGTH = 60.0  # sim seconds per full day (4 equal phases)


def time_of_day(sim_time: float, day_length: float = DEFAULT_DAY_LENGTH) -> str:
    """The current phase. The day wraps every `day_length` sim seconds."""
    frac = (sim_time % day_length) / day_length
    return PHASES[min(int(frac * len(PHASES)), len(PHASES) - 1)]


class Schedule:
    """Maps a time-of-day phase to a goal string for one agent."""

    def __init__(self, by_phase: dict[str, str]) -> None:
        self.by_phase = dict(by_phase)

    def goal_for(self, phase: str) -> str | None:
        return self.by_phase.get(phase)
