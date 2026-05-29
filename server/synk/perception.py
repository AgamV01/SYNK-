"""Perception: what an agent senses on a given tick, scoped by sense radius and zone."""

from __future__ import annotations

from dataclasses import dataclass, field

from .geometry import Vec3
from .world import Entity, World, WorldEvent

DEFAULT_SENSE_RADIUS = 10.0
DEFAULT_EVENT_RECENCY_TICKS = 2


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
    event_recency_ticks: int = DEFAULT_EVENT_RECENCY_TICKS,
    index: object | None = None,
) -> Percept:
    """Build a `Percept` for `agent`.

    `nearby` is every entity within `sense_radius` (xz) in the agent's zone, self
    excluded. `events` is recent world events in the same zone, within sense radius,
    not sourced by the agent itself. Pass a `SpatialIndex` (`index`) to answer the
    neighborhood query in ~O(1); otherwise the world is scanned linearly.
    """
    if index is not None:
        nearby = index.within_radius(
            agent.position, sense_radius, zone=agent.zone, exclude_id=agent.id
        )
    else:
        nearby = world.within_radius(
            agent.position,
            sense_radius,
            zone=agent.zone,
            exclude_id=agent.id,
        )
    events = [
        e
        for e in world.recent_events(within_ticks=event_recency_ticks)
        if e.zone == agent.zone
        and e.source_id != agent.id
        and agent.position.distance_to(e.position) <= sense_radius
    ]
    return Percept(
        agent_id=agent.id,
        position=agent.position,
        tick=world.tick,
        nearby=nearby,
        events=events,
    )
