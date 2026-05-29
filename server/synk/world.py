"""World state: entities, zones, spatial queries, and the tick clock."""

from __future__ import annotations

from dataclasses import dataclass, field

from .geometry import Vec3


@dataclass
class Entity:
    """Anything that exists at a position within a zone."""

    id: str
    position: Vec3 = field(default_factory=Vec3)
    zone: str = "default"


@dataclass
class Player(Entity):
    """A connected human player. The server owns the authoritative copy."""

    name: str = ""
    facing: float = 0.0


@dataclass
class Agent(Entity):
    """An NPC. Brain and memory are attached later (see brains/ and memory)."""

    name: str = ""
    facing: float = 0.0
    personality: str = ""
    current_action: str = "idle"
    goal: str | None = None
