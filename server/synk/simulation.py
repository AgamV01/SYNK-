"""The fixed-timestep simulation loop.

Each tick runs perceive -> decide -> apply for every agent using the cheap reactive
path only. Expensive LLM work is dispatched as off-tick async tasks; their results
are drained back into the world as events on a later tick. The loop never awaits an
LLM call (spec section 2)."""

from __future__ import annotations

import asyncio
import math
from typing import TYPE_CHECKING

from . import actions
from .brains.base import Face, Idle, MoveTo, Wander
from .geometry import Vec3
from .perception import DEFAULT_SENSE_RADIUS, perceive
from .world import Agent, World

if TYPE_CHECKING:
    from .brains.base import Brain

AGENT_SPEED = 2.0  # world units per second


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

    @staticmethod
    def _sense_radius(brain: Brain) -> float:
        radius = getattr(brain, "sense_radius", None)
        if radius is None:
            reactive = getattr(brain, "reactive", None)
            radius = getattr(reactive, "sense_radius", DEFAULT_SENSE_RADIUS)
        return radius

    def _apply(self, agent: Agent, action) -> None:
        """Apply an action chosen on the tick. Locomotion is integrated here; discrete
        deliberative actions are delegated to actions.apply_action (which emits events)."""
        if isinstance(action, MoveTo):
            delta = action.target - agent.position
            dist = delta.length_xz()
            if dist > 1e-6:
                stepd = min(AGENT_SPEED * self.dt, dist)
                direction = Vec3(delta.x, 0.0, delta.z).normalize()
                agent.position = agent.position + direction * stepd
                agent.facing = math.atan2(direction.z, direction.x)
            agent.current_action = "move_to"
        elif isinstance(action, Face):
            target = self.world.try_get(action.target_id)
            if target is not None:
                d = target.position - agent.position
                agent.facing = math.atan2(d.z, d.x)
            agent.current_action = "face"
        elif isinstance(action, Wander):
            agent.current_action = "wander"
        elif isinstance(action, Idle):
            agent.current_action = "idle"
        else:
            actions.apply_action(self.world, agent, action)

    def step(self) -> None:
        """One tick: perceive -> decide -> apply for each registered agent, then advance."""
        for agent_id, brain in self.brains.items():
            agent = self.world.try_get(agent_id)
            if not isinstance(agent, Agent):
                continue
            percept = perceive(self.world, agent, self._sense_radius(brain))
            action = brain.decide(agent, percept)
            self._apply(agent, action)
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
