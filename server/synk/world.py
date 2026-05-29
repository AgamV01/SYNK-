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
