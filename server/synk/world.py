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
class WorldEvent:
    """Something that happened in the world, perceivable by nearby agents."""

    kind: str
    source_id: str
    zone: str
    tick: int
    position: Vec3 = field(default_factory=Vec3)
    salience: float = 0.0
    payload: dict = field(default_factory=dict)


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
        self.tick: int = 0
        self.sim_time: float = 0.0

    def advance(self, dt: float) -> None:
        """Advance the clock by one tick of `dt` seconds."""
        if dt < 0.0:
            raise ValueError("dt must be non-negative")
        self.tick += 1
        self.sim_time += dt

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

    def get(self, entity_id: str) -> Entity:
        try:
            return self._entities[entity_id]
        except KeyError:
            raise KeyError(f"no entity with id {entity_id!r}") from None

    def try_get(self, entity_id: str) -> Entity | None:
        return self._entities.get(entity_id)

    def all(self) -> list[Entity]:
        return list(self._entities.values())

    def by_zone(self, zone: str) -> list[Entity]:
        return [e for e in self._entities.values() if e.zone == zone]

    def within_radius(
        self,
        center: Vec3,
        radius: float,
        zone: str,
        exclude_id: str | None = None,
    ) -> list[Entity]:
        """Entities within `radius` of `center` on the xz-plane, scoped to `zone`.

        Distance is inclusive of the boundary. Entities in other zones are
        never returned, so perception cannot leak across zones.
        """
        out: list[Entity] = []
        for e in self._entities.values():
            if e.zone != zone or e.id == exclude_id:
                continue
            if center.distance_to(e.position) <= radius:
                out.append(e)
        return out
