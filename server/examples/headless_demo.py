#!/usr/bin/env python
"""Headless SYNK demo: spawn agents, tick the world, watch the reactive brain.

Run it:
    python examples/headless_demo.py            # print a tick log
    python examples/headless_demo.py --ticks 80
    python examples/headless_demo.py --selftest  # assert behavior, exit non-zero on failure

No server, no API key, no rendering — just the runtime. The movement stepper here
is a minimal stand-in; the authoritative per-tick apply lives in the Simulation loop.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import sys

from synk.brains.base import Action, Emote, Face, Idle, MoveTo, Wander
from synk.brains.reactive import ReactiveBrain
from synk.geometry import Vec3
from synk.pathfinding import Grid
from synk.perception import perceive
from synk.world import Agent, Player, World

DT = 0.1  # seconds per tick (10 Hz)
AGENT_SPEED = 2.0  # world units per second


def apply_action(world: World, agent: Agent, action: Action) -> None:
    """Mutate the agent according to its chosen action. Minimal demo physics."""
    if isinstance(action, MoveTo):
        delta = action.target - agent.position
        dist = delta.length_xz()
        if dist > 1e-6:
            step = min(AGENT_SPEED * DT, dist)
            direction = Vec3(delta.x, 0.0, delta.z).normalize()
            agent.position = agent.position + direction * step
            agent.facing = math.atan2(direction.z, direction.x)
        agent.current_action = "move_to"
    elif isinstance(action, Face):
        target = world.try_get(action.target_id)
        if target is not None:
            d = target.position - agent.position
            agent.facing = math.atan2(d.z, d.x)
        agent.current_action = "face"
    elif isinstance(action, Emote):
        agent.current_action = action.emote
    elif isinstance(action, Wander):
        agent.current_action = "wander"
    else:  # Idle or anything unhandled in this minimal stepper
        agent.current_action = "idle"


def step(world: World, agents: list[tuple[Agent, ReactiveBrain]]) -> None:
    """Advance the world by one tick: perceive -> decide -> apply for each agent."""
    decisions = [
        (agent, brain.decide(agent, perceive(world, agent, brain.sense_radius)))
        for agent, brain in agents
    ]
    for agent, action in decisions:
        apply_action(world, agent, action)
    world.advance(DT)


def build_approach_scene() -> tuple[World, list[tuple[Agent, ReactiveBrain]], Player]:
    """One agent and one stationary player a few metres away in the same zone."""
    world = World()
    agent = Agent(id="npc_greeter", name="Gus", position=Vec3(0, 0, 0), zone="room")
    player = Player(id="player_1", name="Ada", position=Vec3(8, 0, 0), zone="room")
    world.add(agent)
    world.add(player)
    brain = ReactiveBrain(arrive_radius=1.5)
    return world, [(agent, brain)], player


def run_log(ticks: int) -> None:
    world, agents, player = build_approach_scene()
    print(f"SYNK headless demo — {ticks} ticks @ {1 / DT:.0f} Hz")
    for _ in range(ticks):
        step(world, agents)
        agent = agents[0][0]
        print(
            f"tick {world.tick:3d}  {agent.id} "
            f"pos=({agent.position.x:5.2f},{agent.position.z:5.2f}) "
            f"facing={agent.facing:5.2f} action={agent.current_action}"
        )


def build_obstacle_scene() -> tuple[World, list[tuple[Agent, ReactiveBrain]], Player, Grid]:
    """Agent and player on opposite sides of a wall (col 3, rows 0-5; gap at row 6)."""
    grid = Grid(0, 0, 7, 7, 1.0)
    for row in range(6):
        grid.block((3, row))
    world = World()
    agent = Agent(id="npc_walker", name="Bo", position=grid.cell_center((0, 3)), zone="room")
    player = Player(id="player_1", name="Ada", position=grid.cell_center((6, 3)), zone="room")
    world.add(agent)
    world.add(player)
    brain = ReactiveBrain(arrive_radius=1.0, grid=grid, sense_radius=50.0)
    return world, [(agent, brain)], player, grid


def _selftest_approach() -> None:
    world, agents, player = build_approach_scene()
    agent, brain = agents[0]
    start_dist = agent.position.distance_to(player.position)
    for _ in range(100):
        step(world, agents)
    end_dist = agent.position.distance_to(player.position)
    assert world.tick == 100, f"expected 100 ticks, got {world.tick}"
    assert end_dist < start_dist, "agent should have approached the player"
    assert end_dist <= brain.arrive_radius + 1e-6, (
        f"agent should have reached the player (dist {end_dist:.3f})"
    )
    assert agent.current_action == "face", "agent should face the player on arrival"
    print("SELFTEST PASS: agent approached and faced the player")


def _selftest_obstacle() -> None:
    world, agents, player, grid = build_obstacle_scene()
    agent, brain = agents[0]
    start_dist = agent.position.distance_to(player.position)
    max_z = agent.position.z
    for _ in range(400):
        step(world, agents)
        max_z = max(max_z, agent.position.z)
        assert not grid.is_blocked(grid.world_to_cell(agent.position)), (
            "agent walked into a blocked cell"
        )
        if agent.position.distance_to(player.position) <= brain.arrive_radius:
            break
    end_dist = agent.position.distance_to(player.position)
    assert end_dist <= brain.arrive_radius + 1e-6, (
        f"agent should have reached the player around the wall (dist {end_dist:.3f})"
    )
    assert end_dist < start_dist
    # Must have detoured toward the gap (row 6 center z ~ 6.5) rather than going straight.
    assert max_z > 5.0, f"agent did not detour around the wall (max_z={max_z:.2f})"
    print("SELFTEST PASS: agent navigated around the obstacle")


def _selftest_greeting() -> None:
    world, agents, player = build_approach_scene()
    agent, brain = agents[0]
    # Move the player adjacent and have them speak; the agent should greet back.
    player.position = Vec3(1.0, 0, 0)
    percept = perceive(world, agent, brain.sense_radius)
    result = asyncio.run(brain.converse(agent, percept, "hello, barkeep"))
    assert "Gus" in result.text, f"greeting should name the agent: {result.text!r}"
    assert "hello, barkeep" in result.text, f"greeting should echo the player: {result.text!r}"
    print(f"SELFTEST PASS: agent greeted the player -> {result.text!r}")


def run_selftest() -> None:
    _selftest_approach()
    _selftest_obstacle()
    _selftest_greeting()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SYNK headless demo")
    parser.add_argument("--ticks", type=int, default=60)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        run_selftest()
    else:
        run_log(args.ticks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
