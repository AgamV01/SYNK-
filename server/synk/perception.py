"""Perception: what an agent senses on a given tick, scoped by sense radius and zone."""

from __future__ import annotations

from dataclasses import dataclass, field

from .geometry import Vec3
from .world import Entity, WorldEvent


@dataclass
class Percept:
    """A snapshot of an agent's surroundings for one tick."""

    agent_id: str
    position: Vec3
    tick: int
    nearby: list[Entity] = field(default_factory=list)
    events: list[WorldEvent] = field(default_factory=list)
