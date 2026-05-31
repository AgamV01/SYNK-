"""Load a world from a declarative YAML file.

Worlds-as-data: instead of hand-coding `populate_demo`, a world (its obstacles,
navigation grid, agents, daily schedules and initial relationships) is described in
a YAML file and loaded here. The loader is provider-agnostic — it records each
agent's *brain kind* as a string and leaves provider selection / brain construction
to the caller (the server), so the same file works with Mock or a real LLM."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .geometry import Vec3
from .memory import MemoryStore
from .pathfinding import Grid, Obstacle
from .relationships import Relationships
from .schedule import DEFAULT_DAY_LENGTH, Schedule
from .world import Agent, Portal, World, Zone

# Recognized brain kinds a world file may request per agent.
BRAIN_KINDS = ("llm", "reactive")


@dataclass
class LoadedWorld:
    """Everything a server needs to wire up a Simulation from a world file.

    `brains` maps agent id -> brain kind string; the caller builds the actual Brain
    (so this module never imports a provider). Agents are already added to `world`
    with a MemoryStore and (optionally seeded) Relationships attached."""

    world: World
    obstacles: list[Obstacle] = field(default_factory=list)
    grid: Grid | None = None
    schedules: dict[str, Schedule] = field(default_factory=dict)
    brains: dict[str, str] = field(default_factory=dict)
    day_length: float = DEFAULT_DAY_LENGTH
    name: str = "world"


def _obstacles_from(data: Mapping) -> list[Obstacle]:
    out: list[Obstacle] = []
    for entry in data.get("obstacles", []) or []:
        out.append(Obstacle(center=Vec3.from_list(entry["center"]), radius=float(entry["radius"])))
    return out


def _grid_from(data: Mapping, obstacles: list[Obstacle]) -> Grid | None:
    spec = data.get("grid")
    if not spec:
        return None
    return Grid.from_obstacles(
        float(spec["min_x"]),
        float(spec["min_z"]),
        int(spec["cols"]),
        int(spec["rows"]),
        float(spec["cell_size"]),
        obstacles,
    )


def _add_zones_and_portals(world: World, data: Mapping) -> None:
    """Register declared zones and portals into the world's zone graph."""
    for zone in data.get("zones", []) or []:
        world.add_zone(Zone(id=zone["id"], name=zone.get("name", "")))
    for portal in data.get("portals", []) or []:
        world.add_portal(
            Portal(
                from_zone=portal["from"],
                to_zone=portal["to"],
                position=Vec3.from_list(portal["position"]),
                target=Vec3.from_list(portal["target"]),
                radius=float(portal.get("radius", 1.5)),
            )
        )


def build_world(data: Mapping) -> LoadedWorld:
    """Build a LoadedWorld from an already-parsed mapping (see `load_world_file`)."""
    world = World()
    _add_zones_and_portals(world, data)
    obstacles = _obstacles_from(data)
    grid = _grid_from(data, obstacles)
    schedules: dict[str, Schedule] = {}
    brains: dict[str, str] = {}
    for spec in data.get("agents", []) or []:
        agent = Agent(
            id=spec["id"],
            name=spec.get("name", ""),
            personality=spec.get("personality", ""),
            position=Vec3.from_list(spec.get("position", [0.0, 0.0, 0.0])),
            zone=spec.get("zone", "default"),
        )
        if spec.get("goal"):
            agent.goal = spec["goal"]
        agent.memory = MemoryStore()  # duck-typed attachment used by LLMBrain + reflection
        relationships = Relationships()
        for other_id, value in (spec.get("relationships") or {}).items():
            relationships.adjust(str(other_id), float(value))
        agent.relationships = relationships
        world.add(agent)
        kind = spec.get("brain", "llm")
        if kind not in BRAIN_KINDS:
            raise ValueError(f"agent {agent.id!r}: unknown brain kind {kind!r}")
        brains[agent.id] = kind
        sched = spec.get("schedule")
        if sched:
            schedules[agent.id] = Schedule(dict(sched))
    return LoadedWorld(
        world=world,
        obstacles=obstacles,
        grid=grid,
        schedules=schedules,
        brains=brains,
        day_length=float(data.get("day_length", DEFAULT_DAY_LENGTH)),
        name=str(data.get("name", "world")),
    )


def load_world_file(path: str | Path) -> LoadedWorld:
    """Parse a YAML world file and build a LoadedWorld. Raises on missing file or
    malformed top-level structure (a mapping is required)."""
    text = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, Mapping):
        raise ValueError(f"world file {path!s} must be a mapping at the top level")
    return build_world(data)
