"""Low-frequency reflection: agents periodically summarize recent memories into a
new, salient memory. Scheduled per-agent and run off the tick path (async)."""

from __future__ import annotations


class ReflectionScheduler:
    """Tracks when each agent is next due to reflect. `interval` is in sim seconds."""

    def __init__(self, interval: float) -> None:
        if interval <= 0:
            raise ValueError("interval must be positive")
        self.interval = interval
        self._next_due: dict[str, float] = {}

    def due(self, agent_id: str, now: float) -> bool:
        """True if `agent_id` is due to reflect at time `now`. The first call for an
        agent only schedules its first reflection one interval out (never due yet)."""
        nxt = self._next_due.get(agent_id)
        if nxt is None:
            self._next_due[agent_id] = now + self.interval
            return False
        return now >= nxt

    def mark(self, agent_id: str, now: float) -> None:
        """Record that the agent just reflected; schedule the next one."""
        self._next_due[agent_id] = now + self.interval
