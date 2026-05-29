from __future__ import annotations

import asyncio

import pytest

from synk.brains.llm import LLMBrain
from synk.brains.reactive import ReactiveBrain
from synk.geometry import Vec3
from synk.memory import MemoryItem, MemoryStore
from synk.persistence import Persistence
from synk.reflection import ReflectionScheduler
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


class ActionJSONProvider:
    name = "json"

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        return '{"speech": "Take this!", "action": {"type": "emote", "emote": "wave"}}'


async def test_drain_results_emits_spoke_and_action_events() -> None:
    world = World()
    world.add(Agent(id="npc1", name="Gus", position=Vec3(0, 0, 0), zone="room"))
    sim = Simulation(world, dt=0.001)
    sim.register("npc1", LLMBrain(provider=ActionJSONProvider()))
    await sim.dispatch_converse("npc1", "hello")
    events = sim.drain_results()
    kinds = [e.kind for e in events]
    assert "spoke" in kinds
    assert "emoted" in kinds
    spoke = next(e for e in events if e.kind == "spoke")
    assert spoke.payload["text"] == "Take this!"
    assert sim._results == []  # drained


class ExplodingProvider:
    """Raises if the tick ever calls an LLM."""

    name = "exploding"

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        raise AssertionError("LLM provider must never be called on the tick path")


def test_no_llm_call_on_tick_path() -> None:
    world = World()
    world.add(Agent(id="npc1", position=Vec3(0, 0, 0), zone="room"))
    world.add(Player(id="p1", position=Vec3(3, 0, 0), zone="room"))
    sim = Simulation(world, dt=0.1)
    sim.register("npc1", LLMBrain(provider=ExplodingProvider()))
    # Many ticks with a player present (which drives decide()): the provider that
    # explodes-on-call is never invoked, proving the tick path does zero LLM I/O.
    for _ in range(50):
        sim.step()
    assert world.tick == 50


async def test_persistence_hook_enqueues_snapshot() -> None:
    world = World()
    world.add(Agent(id="npc1", position=Vec3(0, 0, 0), zone="room"))
    persistence = Persistence(":memory:")
    await persistence.connect()
    try:
        sim = Simulation(world, dt=0.001, persistence=persistence, save_every=1)
        sim.step()  # tick becomes 1; 1 % 1 == 0 -> snapshot enqueued (tick-safe)
        assert persistence.pending > 0
        await persistence.flush()
        cursor = await persistence.db.execute("SELECT COUNT(*) FROM entities")
        (count,) = await cursor.fetchone()
        assert count == 1
    finally:
        await persistence.close()


async def test_reflection_hook_dispatches_off_tick() -> None:
    world = World()
    agent = Agent(id="npc1", position=Vec3(0, 0, 0), zone="room")
    agent.memory = MemoryStore()
    agent.memory.add(MemoryItem("a thing happened", ts=0.0, salience=1.0))
    world.add(agent)
    sim = Simulation(world, dt=0.1, reflection=ReflectionScheduler(interval=0.05))
    sim.register("npc1", ReactiveBrain())
    sim.step()  # sim_time 0->0.1; first due() call schedules (not yet due)
    sim.step()  # sim_time 0.1; now due -> reflect dispatched off-tick
    assert sim.pending_count >= 1
    await asyncio.gather(*sim._pending)
    assert len(agent.memory) == 2  # reflection added a salient memory
