"""The fixed-timestep simulation loop.

Each tick runs perceive -> decide -> apply for every agent using the cheap reactive
path only. Expensive LLM work is dispatched as off-tick async tasks; their results
are drained back into the world as events on a later tick. The loop never awaits an
LLM call (spec section 2)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from .world import World

if TYPE_CHECKING:
    from .brains.base import Brain


class Simulation:
    def __init__(self, world: World, dt: float = 0.1) -> None:
        if dt <= 0:
            raise ValueError("dt must be positive")
        self.world = world
        self.dt = dt
        self.brains: dict[str, Brain] = {}
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def register(self, agent_id: str, brain: Brain) -> None:
        self.brains[agent_id] = brain

    def step(self) -> None:
        """Advance the world by one tick. (Per-agent perceive/decide/apply added next.)"""
        self.world.advance(self.dt)

    async def run(self, max_ticks: int | None = None) -> None:
        """Run the fixed-timestep loop until stopped (or `max_ticks` reached)."""
        self._running = True
        count = 0
        try:
            while self._running:
                self.step()
                count += 1
                if max_ticks is not None and count >= max_ticks:
                    break
                await asyncio.sleep(self.dt)
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False
