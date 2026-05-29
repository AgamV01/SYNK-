from __future__ import annotations

import asyncio

import pytest

from synk.brains.llm import LLMBrain
from synk.brains.reactive import ReactiveBrain
from synk.geometry import Vec3
from synk.simulation import Simulation
from synk.world import Agent, Player, World


class SlowProvider:
    name = "slow"

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        await asyncio.sleep(0.02)
        return "a considered reply"


def test_rejects_bad_dt() -> None:
    with pytest.raises(ValueError):
        Simulation(World(), dt=0.0)


async def test_run_advances_clock_and_stops_at_max_ticks() -> None:
    sim = Simulation(World(), dt=0.001)
    await sim.run(max_ticks=5)
    assert sim.world.tick == 5
    assert sim.running is False


async def test_stop_halts_loop() -> None:
    sim = Simulation(World(), dt=0.001)
    task = asyncio.create_task(sim.run())
    await asyncio.sleep(0.02)
    sim.stop()
    await task
    assert sim.running is False
    assert sim.world.tick > 0


def test_step_moves_agent_toward_player() -> None:
    world = World()
    agent = Agent(id="npc1", position=Vec3(0, 0, 0), zone="room")
    player = Player(id="p1", position=Vec3(8, 0, 0), zone="room")
    world.add(agent)
    world.add(player)
    sim = Simulation(world, dt=0.1)
    sim.register("npc1", ReactiveBrain(arrive_radius=1.5))
    sim.step()
    assert agent.position.x > 0.0  # moved toward the player
    assert agent.current_action == "move_to"
    assert world.tick == 1


def test_step_faces_player_when_close() -> None:
    world = World()
    agent = Agent(id="npc1", position=Vec3(0, 0, 0), zone="room")
    player = Player(id="p1", position=Vec3(1.0, 0, 0), zone="room")
    world.add(agent)
    world.add(player)
    sim = Simulation(world, dt=0.1)
    sim.register("npc1", ReactiveBrain(arrive_radius=1.5))
    sim.step()
    assert agent.current_action == "face"


async def test_converse_dispatched_off_tick() -> None:
    world = World()
    world.add(Agent(id="npc1", name="Gus", position=Vec3(0, 0, 0), zone="room"))
    sim = Simulation(world, dt=0.001)
    sim.register("npc1", LLMBrain(provider=SlowProvider()))
    task = sim.dispatch_converse("npc1", "hello")
    assert sim.pending_count == 1
    # The tick loop keeps running while the slow LLM call is in flight.
    sim.step()
    sim.step()
    assert world.tick == 2
    assert not task.done()  # still pending; the tick never awaited it
    await task
    assert ("npc1", task.result()) in sim._results
    assert task.result().text == "a considered reply"
