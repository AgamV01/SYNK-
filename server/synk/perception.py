"""Perception: what an agent senses on a given tick, scoped by sense radius and zone."""

from __future__ import annotations

from dataclasses import dataclass, field

from .geometry import Vec3
from .world import Entity, World, WorldEvent

DEFAULT_SENSE_RADIUS = 10.0


@dataclass
class Percept:
    """A snapshot of an agent's surroundings for one tick."""

    agent_id: str
    position: Vec3
    tick: int
    nearby: list[Entity] = field(default_factory=list)
    events: list[WorldEvent] = field(default_factory=list)


def perceive(
    world: World,
    agent: Entity,
    sense_radius: float = DEFAULT_SENSE_RADIUS,
) -> Percept:
    """Build a `Percept` for `agent`: entities within `sense_radius` (xz), excluding self."""
    nearby = world.within_radius(
        agent.position,
        sense_radius,
        zone=agent.zone,
        exclude_id=agent.id,
    )
    return Percept(
        agent_id=agent.id,
        position=agent.position,
        tick=world.tick,
        nearby=nearby,
    )
