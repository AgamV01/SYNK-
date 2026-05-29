from __future__ import annotations

import asyncio

import pytest

from synk.simulation import Simulation
from synk.world import World


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
