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
from .brains.base import ConverseResult, Face, Idle, MoveTo, Wander
from .geometry import Vec3
from .memory import score_event_salience
from .perception import DEFAULT_SENSE_RADIUS, perceive
from .reflection import reflect
from .world import Agent, World, WorldEvent

if TYPE_CHECKING:
    from .brains.base import Brain
    from .brains.providers import Provider
    from .persistence import Persistence
    from .reflection import ReflectionScheduler

AGENT_SPEED = 2.0  # world units per second


class Simulation:
    def __init__(
        self,
        world: World,
        dt: float = 0.1,
        persistence: Persistence | None = None,
        reflection: ReflectionScheduler | None = None,
        reflection_provider: Provider | None = None,
        save_every: int = 50,
    ) -> None:
        if dt <= 0:
            raise ValueError("dt must be positive")
        self.world = world
        self.dt = dt
        self.brains: dict[str, Brain] = {}
        self.persistence = persistence
        self.reflection = reflection
        self.reflection_provider = reflection_provider
        self.save_every = save_every
        self._running = False
        self._pending: list[asyncio.Task] = []
        self._results: list[tuple[str, ConverseResult]] = []

    @property
    def running(self) -> bool:
        return self._running

    def register(self, agent_id: str, brain: Brain) -> None:
        self.brains[agent_id] = brain

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def dispatch_converse(self, agent_id: str, utterance: str) -> asyncio.Task:
        """Kick off an agent's deliberative reply as an off-tick async task.

        Returns immediately with the Task — the tick loop never awaits it. The
        result lands in `_results` for the loop to drain into world events later."""
        brain = self.brains[agent_id]
        agent = self.world.try_get(agent_id)
        if not isinstance(agent, Agent):
            raise KeyError(f"no agent {agent_id!r} to converse")
        percept = perceive(self.world, agent, self._sense_radius(brain))

        async def _runner() -> ConverseResult:
            result = await brain.converse(agent, percept, utterance)
            self._results.append((agent_id, result))
            return result

        task = asyncio.create_task(_runner())
        self._pending.append(task)
        return task

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

    def drain_results(self) -> list[WorldEvent]:
        """Fold completed off-tick converse results back into the world as events: a
        `spoke` event for the dialogue line, plus any structured action's event."""
        self._pending = [t for t in self._pending if not t.done()]
        batch = self._results
        self._results = []
        events: list[WorldEvent] = []
        for agent_id, result in batch:
            agent = self.world.try_get(agent_id)
            if not isinstance(agent, Agent):
                continue
            spoke = WorldEvent(
                kind="spoke",
                source_id=agent_id,
                zone=agent.zone,
                tick=self.world.tick,
                position=agent.position,
                salience=score_event_salience("spoke"),
                payload={"text": result.text},
            )
            self.world.emit_event(spoke)
            events.append(spoke)
            if result.action is not None:
                action_event = actions.apply_action(self.world, agent, result.action)
                if action_event is not None:
                    events.append(action_event)
        return events

    def _maybe_reflect(self) -> int:
        """Dispatch off-tick reflection for any agent whose timer is due. Returns the
        number dispatched. Reflection runs async (never on the tick)."""
        if self.reflection is None:
            return 0
        dispatched = 0
        for agent_id in self.brains:
            agent = self.world.try_get(agent_id)
            memory = getattr(agent, "memory", None)
            if memory is None or not hasattr(memory, "recall_recent"):
                continue
            if self.reflection.due(agent_id, self.world.sim_time):
                task = asyncio.create_task(
                    reflect(memory, self.world.sim_time, self.reflection_provider)
                )
                self._pending.append(task)
                self.reflection.mark(agent_id, self.world.sim_time)
                dispatched += 1
        return dispatched

    def _maybe_persist(self) -> None:
        """Queue a world snapshot every `save_every` ticks. Enqueue only (tick-safe);
        the actual disk write is flushed off-tick in run()."""
        if self.persistence is not None and self.world.tick % self.save_every == 0:
            self.persistence.save_world(self.world)

    def step(self) -> None:
        """One tick: drain off-tick results, then perceive -> decide -> apply, then advance."""
        self.drain_results()
        for agent_id, brain in self.brains.items():
            agent = self.world.try_get(agent_id)
            if not isinstance(agent, Agent):
                continue
            percept = perceive(self.world, agent, self._sense_radius(brain))
            action = brain.decide(agent, percept)
            self._apply(agent, action)
        self._maybe_reflect()
        self.world.advance(self.dt)
        self._maybe_persist()

    async def run(self, max_ticks: int | None = None) -> None:
        """Run the fixed-timestep loop until stopped (or `max_ticks` reached)."""
        self._running = True
        count = 0
        try:
            while self._running:
                self.step()
                if self.persistence is not None:
                    await self.persistence.flush()  # off-tick disk write
                count += 1
                if max_ticks is not None and count >= max_ticks:
                    break
                await asyncio.sleep(self.dt)
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False
