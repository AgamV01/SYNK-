#!/usr/bin/env python
"""Benchmark SYNK's hybrid-brain cost claims, headlessly and with no API key:

  1. An idle world spends ~zero — 0 LLM calls regardless of NPC count.
  2. Per-tick cost scales with the spatial index, not O(agents^2).

    python tools/benchmark.py
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

from synk.brains.llm import LLMBrain  # noqa: E402
from synk.brains.providers import MockProvider  # noqa: E402
from synk.brains.reactive import ReactiveBrain  # noqa: E402
from synk.geometry import Vec3  # noqa: E402
from synk.simulation import Simulation  # noqa: E402
from synk.world import Agent, World  # noqa: E402


def _world(n: int, brain_factory) -> tuple[World, Simulation]:
    world = World(max_events=4000)
    sim = Simulation(world, dt=0.1)
    side = math.ceil(math.sqrt(n))
    for i in range(n):
        agent = Agent(id=f"a{i}", position=Vec3((i % side) * 3.0, 0, (i // side) * 3.0), zone="bench")
        world.add(agent)
        sim.register(agent.id, brain_factory())
    return world, sim


def tick_rate(n: int, ticks: int = 200) -> tuple[float, float]:
    _, sim = _world(n, ReactiveBrain)
    start = time.perf_counter()
    for _ in range(ticks):
        sim.step()
    elapsed = time.perf_counter() - start
    return ticks / elapsed, (elapsed / ticks) * 1000.0


def idle_llm_calls(n: int = 100, ticks: int = 200) -> int:
    _, sim = _world(n, lambda: LLMBrain(provider=MockProvider()))
    for _ in range(ticks):
        sim.step()  # no events -> deliberation never fires
    return sim.metrics()["llm_calls"]


def main() -> int:
    print("SYNK benchmark (reactive tick cost; MockProvider; no API key)\n")
    calls = idle_llm_calls()
    print(f"Idle cost: 100 NPCs x 200 ticks, no events  ->  {calls} LLM calls\n")
    print("| agents | ticks/sec | ms/tick |")
    print("|-------:|----------:|--------:|")
    for n in (10, 50, 100, 250, 500):
        tps, mspt = tick_rate(n)
        print(f"| {n:>6} | {tps:>9,.0f} | {mspt:>7.3f} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
