"""Agent memory: salient items with timestamps, decay, and recall."""

from __future__ import annotations

import math
from dataclasses import dataclass

# How memorable each kind of event is. Higher = more likely to be recalled and
# to survive decay. Unknown kinds fall back to DEFAULT_SALIENCE.
SALIENCE_BY_KIND: dict[str, float] = {
    "gave_item": 3.0,
    "goal_changed": 2.5,
    "handoff": 2.0,
    "spoke": 1.5,
    "emoted": 1.0,
    "moved": 0.5,
}
DEFAULT_SALIENCE = 1.0


def score_event_salience(kind: str) -> float:
    """Baseline salience for a memory formed from an event of the given kind."""
    return SALIENCE_BY_KIND.get(kind, DEFAULT_SALIENCE)


@dataclass
class MemoryItem:
    """One remembered fact or event.

    `ts` is the simulation time (seconds) the memory was formed. `salience` is an
    importance score in [0, inf); higher means more likely to be recalled and to
    survive decay.
    """

    text: str
    ts: float
    salience: float = 1.0


class MemoryStore:
    """A bounded collection of memories. When full, the least salient item is
    evicted (ties broken by age), so important memories persist."""

    def __init__(self, capacity: int = 100) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._items: list[MemoryItem] = []

    def __len__(self) -> int:
        return len(self._items)

    @property
    def items(self) -> list[MemoryItem]:
        return list(self._items)

    def add(self, item: MemoryItem) -> None:
        self._items.append(item)
        if len(self._items) > self.capacity:
            victim = min(self._items, key=lambda m: (m.salience, m.ts))
            self._items.remove(victim)

    def decay(self, dt: float, rate: float = 0.05, floor: float = 0.05) -> None:
        """Multiplicatively decay every memory's salience by exp(-rate*dt), then
        forget items that fall below `floor`. Called periodically by the sim, not
        on the hot tick path."""
        if dt < 0.0:
            raise ValueError("dt must be non-negative")
        factor = math.exp(-rate * dt)
        for item in self._items:
            item.salience *= factor
        self._items = [m for m in self._items if m.salience >= floor]

    def recall_recent(self, n: int) -> list[MemoryItem]:
        """The `n` most recently formed memories, newest first."""
        if n <= 0:
            return []
        return sorted(self._items, key=lambda m: m.ts, reverse=True)[:n]

    def recall_salient(self, k: int) -> list[MemoryItem]:
        """The `k` most salient memories, most salient first (ties: newer first)."""
        if k <= 0:
            return []
        return sorted(self._items, key=lambda m: (m.salience, m.ts), reverse=True)[:k]

    def recall(self, recent_n: int = 5, salient_k: int = 5) -> list[MemoryItem]:
        """Recall = recent ∪ salient. The union of the most recent and the most
        salient memories, deduplicated, returned newest-first. This is what an
        agent's brain reads when forming a response."""
        chosen: dict[int, MemoryItem] = {id(m): m for m in self.recall_recent(recent_n)}
        for m in self.recall_salient(salient_k):
            chosen.setdefault(id(m), m)
        return sorted(chosen.values(), key=lambda m: m.ts, reverse=True)
