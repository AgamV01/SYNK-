"""Agent memory: salient items with timestamps, decay, and recall."""

from __future__ import annotations

from dataclasses import dataclass


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
