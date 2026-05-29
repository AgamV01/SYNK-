#!/usr/bin/env python
"""The tavern: a small example world with three NPCs of distinct personalities,
props, and obstacles. Reused by the demo server and runnable as a headless selftest.

    python examples/tavern.py --selftest
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from synk.brains.reactive import ReactiveBrain
from synk.geometry import Vec3
from synk.pathfinding import Grid, Obstacle
from synk.simulation import Simulation
from synk.world import Agent, Player, World

ZONE = "tavern"


@dataclass
class Tavern:
    world: World
    brains: dict[str, ReactiveBrain]
    obstacles: list[Obstacle]
    grid: Grid


def build_tavern() -> Tavern:
    """Construct the tavern world: 3 personality NPCs + two table obstacles."""
    obstacles = [
        Obstacle(center=Vec3(-4, 0, -2), radius=1.2),  # a big round table
        Obstacle(center=Vec3(5, 0, 1), radius=1.0),  # the hearth
    ]
    grid = Grid.from_obstacles(
        min_x=-15, min_z=-15, cols=30, rows=30, cell_size=1.0, obstacles=obstacles
    )
    world = World()
    agents = [
        Agent(
            id="npc_gus",
            name="Gus",
            personality="a gruff barkeep who has seen every kind of trouble",
            position=Vec3(0, 0, -3),
            zone=ZONE,
        ),
        Agent(
            id="npc_mira",
            name="Mira",
            personality="a curious traveling bard, quick with a song and a question",
            position=Vec3(3, 0, 2),
            zone=ZONE,
        ),
        Agent(
            id="npc_tomas",
            name="Tomas",
            personality="a suspicious city guard who trusts no one",
            position=Vec3(-3, 0, 3),
            zone=ZONE,
        ),
    ]
    for agent in agents:
        world.add(agent)
    brains = {a.id: ReactiveBrain(grid=grid, arrive_radius=1.5) for a in agents}
    return Tavern(world=world, brains=brains, obstacles=obstacles, grid=grid)


def run_selftest() -> None:
    tavern = build_tavern()
    sim = Simulation(tavern.world, dt=0.1)
    for agent_id, brain in tavern.brains.items():
        sim.register(agent_id, brain)
    # A player walks up to Gus.
    tavern.world.add(Player(id="player_1", name="Ada", position=Vec3(0, 0, -1), zone=ZONE))

    for _ in range(80):
        sim.step()

    assert tavern.world.tick == 80
    gus = tavern.world.get("npc_gus")
    assert gus.current_action in {"move_to", "face"}, (
        f"Gus should have engaged the nearby player, got {gus.current_action!r}"
    )
    # The other NPCs ran their reactive loop without error.
    for agent_id in ("npc_mira", "npc_tomas"):
        assert tavern.world.get(agent_id).current_action  # set to some label
    print("SELFTEST PASS: tavern with 3 NPCs ran 80 ticks; Gus engaged the player")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SYNK tavern example")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        run_selftest()
    else:
        tavern = build_tavern()
        print(f"Tavern built: {len(tavern.brains)} NPCs, {len(tavern.obstacles)} obstacles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
