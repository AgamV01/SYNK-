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
