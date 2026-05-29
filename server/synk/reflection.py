"""Low-frequency reflection: agents periodically summarize recent memories into a
new, salient memory. Scheduled per-agent and run off the tick path (async)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .memory import MemoryItem, MemoryStore

if TYPE_CHECKING:
    from .brains.providers import Provider


async def reflect(
    memory: MemoryStore,
    now: float,
    provider: Provider | None = None,
    recent_n: int = 5,
) -> MemoryItem | None:
    """Summarize the agent's recent memories into one new, more-salient memory.

    Async because it may call an LLM. With no provider it produces a templated
    summary, so reflection works with zero API keys. Returns the new memory, or
    None if there is nothing to reflect on."""
    recent = memory.recall_recent(recent_n)
    if not recent:
        return None
    texts = [m.text for m in recent]
    if provider is not None:
        prompt = "Summarize these recent experiences into one salient insight:\n" + "\n".join(
            f"- {t}" for t in texts
        )
        summary = (await provider.generate(prompt)).strip()
    else:
        summary = "Reflection: " + "; ".join(texts)
    # Make the reflection stickier than its constituents so it survives decay.
    salience = max(m.salience for m in recent) + 1.0
    item = MemoryItem(text=summary, ts=now, salience=salience)
    memory.add(item)
    return item


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
