from __future__ import annotations

from pathlib import Path

import pytest

from synk.pathfinding import Grid
from synk.schedule import Schedule
from synk.world import Agent
from synk.worldfile import build_world, load_world_file

TAVERN = Path(__file__).resolve().parents[1] / "worlds" / "tavern.yaml"


def test_loads_tavern_world_file() -> None:
    # B1: the loader reproduces the legacy populate_demo tavern from data.
    loaded = load_world_file(TAVERN)
    assert loaded.name == "tavern"
    assert loaded.day_length == 60.0
    agents = {e.id: e for e in loaded.world.all() if isinstance(e, Agent)}
    assert set(agents) == {"npc_gus", "npc_mira", "npc_tomas"}
    assert agents["npc_gus"].name == "Gus"
    assert agents["npc_gus"].personality == "a gruff barkeep"
    assert agents["npc_gus"].zone == "tavern"
    # Two obstacles and a navigation grid (with some cells blocked).
    assert len(loaded.obstacles) == 2
    assert isinstance(loaded.grid, Grid)
    assert loaded.grid.blocked  # obstacles blocked at least one cell
    # Every NPC has a daily schedule and an LLM brain.
    assert set(loaded.schedules) == {"npc_gus", "npc_mira", "npc_tomas"}
    assert isinstance(loaded.schedules["npc_gus"], Schedule)
    assert loaded.schedules["npc_gus"].goal_for("morning") == "open up and wipe down the bar"
    assert all(kind == "llm" for kind in loaded.brains.values())


def test_agents_get_memory_and_relationships() -> None:
    loaded = load_world_file(TAVERN)
    gus = loaded.world.try_get("npc_gus")
    assert hasattr(gus, "memory") and gus.memory is not None
    assert hasattr(gus, "relationships") and gus.relationships is not None


def test_build_world_seeds_relationships_and_goal() -> None:
    data = {
        "name": "mini",
        "agents": [
            {
                "id": "a",
                "name": "A",
                "position": [1, 0, 2],
                "zone": "z",
                "brain": "reactive",
                "goal": "find the exit",
                "relationships": {"b": -2.0},
            }
        ],
    }
    loaded = build_world(data)
    a = loaded.world.try_get("a")
    assert a.goal == "find the exit"
    assert loaded.brains["a"] == "reactive"
    # Seeded sentiment is reflected in the relationship description.
    desc = " ".join(a.relationships.describe())
    assert "b" in desc


def test_tavern_has_two_zones_and_portals() -> None:
    # B6: the tavern world declares a connected market zone reachable via portals.
    loaded = load_world_file(TAVERN)
    assert set(loaded.world.zones) == {"tavern", "market"}
    assert loaded.world.neighbors("tavern") == {"market"}
    assert loaded.world.neighbors("market") == {"tavern"}


def test_e2e_agent_migrates_between_zones() -> None:
    # B6 (end-to-end): an NPC that walks onto the tavern->market portal migrates and
    # then appears in the market zone, driven by the real loader + Simulation.
    from synk.brains.reactive import ReactiveBrain
    from synk.geometry import Vec3
    from synk.simulation import Simulation
    from synk.world import Agent

    loaded = load_world_file(TAVERN)
    world = loaded.world
    gus = world.try_get("npc_gus")
    assert isinstance(gus, Agent)
    gus.position = Vec3(12, 0, 0)  # standing on the tavern->market portal
    sim = Simulation(world, dt=0.1, day_length=loaded.day_length)
    sim.register("npc_gus", ReactiveBrain())
    sim.step()
    assert gus.zone == "market"
    assert gus.position == Vec3(-10, 0, 0)
    assert any(e.id == "npc_gus" for e in world.by_zone("market"))
    assert all(e.id != "npc_gus" for e in world.by_zone("tavern"))


def test_unknown_brain_kind_raises() -> None:
    with pytest.raises(ValueError):
        build_world({"agents": [{"id": "a", "brain": "telepathy"}]})


def test_non_mapping_world_file_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_world_file(bad)
