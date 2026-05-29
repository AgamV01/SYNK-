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


class World:
    """Holds all entities and the simulation clock. Authoritative."""

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}

    def add(self, entity: Entity) -> None:
        if entity.id in self._entities:
            raise ValueError(f"entity id already present: {entity.id!r}")
        self._entities[entity.id] = entity

    def remove(self, entity_id: str) -> Entity:
        try:
            return self._entities.pop(entity_id)
        except KeyError:
            raise KeyError(f"no entity with id {entity_id!r}") from None

    def __contains__(self, entity_id: object) -> bool:
        return entity_id in self._entities

    def __len__(self) -> int:
        return len(self._entities)
