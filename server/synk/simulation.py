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
from .dialogue import DialogueManager
from .geometry import Vec3
from .memory import MemoryItem, score_event_salience
from .perception import DEFAULT_SENSE_RADIUS, perceive
from .reflection import reflect
from .relationships import sentiment_for
from .schedule import DEFAULT_DAY_LENGTH, Schedule, time_of_day
from .spatial import SpatialIndex
from .world import Agent, World, WorldEvent


def describe_event(event: WorldEvent) -> str:
    """Human/LLM-readable one-liner for a perceived event, used as a memory text."""
    if event.kind == "spoke":
        text = event.payload.get("text", "")
        return f'{event.source_id} said: "{text}"'
    if event.kind == "emoted":
        return f"{event.source_id} emoted {event.payload.get('emote', '')}".strip()
    if event.kind == "gave_item":
        return f"{event.source_id} gave {event.payload.get('item', 'something')}"
    return f"{event.source_id} {event.kind}"

if TYPE_CHECKING:
    from .brains.base import Brain
    from .brains.providers import Provider
    from .persistence import Persistence
    from .reflection import ReflectionScheduler

AGENT_SPEED = 2.0  # world units per second


class NpcConversation:
    """Drives a bounded, alternating conversation between two LLM NPCs. Each turn is an
    off-tick `dispatch_converse`; the spoken line is recorded into a group conversation
    (so the next speaker has context) and surfaced to nearby players as overheard speech."""

    def __init__(
        self,
        sim: Simulation,
        a_id: str,
        b_id: str,
        turns: int = 4,
        interval: float = 1.5,
    ) -> None:
        self.sim = sim
        self.a = a_id
        self.b = b_id
        self.convo_id = f"npc:{a_id}:{b_id}"
        self.turns_remaining = turns
        self.interval = interval
        self.next_speaker = a_id
        self.last_turn = float("-inf")
        self.in_flight = False
        self._task = None
        self._speaker: str | None = None
        sim.dialogue.group(self.convo_id, [a_id, b_id])

    @property
    def done(self) -> bool:
        return self.turns_remaining <= 0 and not self.in_flight

    def tick(self, now: float) -> None:
        # Collect a completed turn before starting the next.
        if self.in_flight:
            if self._task is not None and self._task.done():
                result = None
                try:
                    result = self._task.result()
                except Exception:  # pragma: no cover - provider failure is non-fatal
                    result = None
                if result is not None and self._speaker is not None:
                    self.sim.dialogue.route_group_message(self.convo_id, self._speaker, result.text)
                self.in_flight = False
                self._task = None
            else:
                return
        if self.turns_remaining <= 0 or now - self.last_turn < self.interval:
            return
        speaker_id = self.next_speaker
        listener_id = self.b if speaker_id == self.a else self.a
        speaker = self.sim.world.try_get(speaker_id)
        if not isinstance(speaker, Agent):
            self.turns_remaining = 0
            return
        speaker.conversation = self.sim.dialogue.group(self.convo_id)  # context for the LLM
        listener = self.sim.world.try_get(listener_id)
        listener_name = getattr(listener, "name", listener_id)
        self.last_turn = now
        self.turns_remaining -= 1
        self.next_speaker = listener_id
        self._speaker = speaker_id
        self.in_flight = True
        self.sim._metrics["npc_turns"] += 1
        self._task = self.sim.dispatch_converse(
            speaker_id, f"Continue your conversation with {listener_name}. Say one short line."
        )


class Simulation:
    def __init__(
        self,
        world: World,
        dt: float = 0.1,
        persistence: Persistence | None = None,
        reflection: ReflectionScheduler | None = None,
        reflection_provider: Provider | None = None,
        save_every: int = 50,
        memory_decay_every: int = 100,
        deliberate_threshold: float = 1.5,
        deliberate_cooldown: float = 5.0,
        dialogue: DialogueManager | None = None,
        npc_chat: bool = False,
        npc_chat_turns: int = 4,
        npc_chat_interval: float = 1.5,
        npc_chat_cooldown: float = 15.0,
        day_length: float = DEFAULT_DAY_LENGTH,
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
        self.memory_decay_every = memory_decay_every
        self.deliberate_threshold = deliberate_threshold
        self.deliberate_cooldown = deliberate_cooldown
        self._last_deliberation: dict[str, float] = {}
        self.dialogue = dialogue or DialogueManager()
        self.npc_chat = npc_chat
        self.npc_chat_turns = npc_chat_turns
        self.npc_chat_interval = npc_chat_interval
        self.npc_chat_cooldown = npc_chat_cooldown
        self._npc_convos: list[NpcConversation] = []
        self._npc_chat_cooldown_until: dict[frozenset, float] = {}
        self.day_length = day_length
        self.schedules: dict[str, Schedule] = {}
        self._agent_phase: dict[str, str] = {}
        # Cost telemetry — the data behind the hybrid-brain claim.
        self._metrics = {"llm_calls": 0, "deliberations": 0, "reflections": 0, "npc_turns": 0}
        self._running = False
        self._pending: list[asyncio.Task] = []
        self._results: list[tuple[str, ConverseResult]] = []

    def metrics(self) -> dict:
        """Cumulative simulation counters (ticks + off-tick LLM activity)."""
        return {
            **self._metrics,
            "ticks": self.world.tick,
            "sim_time": round(self.world.sim_time, 3),
            "agents": len(self.brains),
        }

    @property
    def running(self) -> bool:
        return self._running

    def register(self, agent_id: str, brain: Brain) -> None:
        self.brains[agent_id] = brain

    def register_schedule(self, agent_id: str, schedule: Schedule) -> None:
        self.schedules[agent_id] = schedule

    def _apply_schedules(self) -> None:
        """At each phase change, set scheduled agents' goals and emit a goal_changed event
        (which others perceive, surfaces to clients, and the reactive layer pursues)."""
        if not self.schedules:
            return
        phase = time_of_day(self.world.sim_time, self.day_length)
        for agent_id, schedule in self.schedules.items():
            if self._agent_phase.get(agent_id) == phase:
                continue
            self._agent_phase[agent_id] = phase
            goal = schedule.goal_for(phase)
            agent = self.world.try_get(agent_id)
            if goal is None or not isinstance(agent, Agent):
                continue
            agent.goal = goal
            self.world.emit_event(
                WorldEvent(
                    kind="goal_changed",
                    source_id=agent_id,
                    zone=agent.zone,
                    tick=self.world.tick,
                    position=agent.position,
                    salience=score_event_salience("goal_changed"),
                    payload={"goal": goal},
                )
            )

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
        self._metrics["llm_calls"] += 1

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
            # Off-tick speech is autonomous (no synchronous addressee) -> overheard.
            spoke.payload["overheard"] = True
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
                self._metrics["reflections"] += 1
                self._metrics["llm_calls"] += 1  # reflect() calls the provider when set
                dispatched += 1
        return dispatched

    def _maybe_persist(self) -> None:
        """Queue a world snapshot every `save_every` ticks. Enqueue only (tick-safe);
        the actual disk write is flushed off-tick in run()."""
        if self.persistence is not None and self.world.tick % self.save_every == 0:
            self.persistence.save_world(self.world)
            for agent_id in self.brains:
                agent = self.world.try_get(agent_id)
                memory = getattr(agent, "memory", None)
                if memory is not None and hasattr(memory, "items"):
                    self.persistence.save_memory(agent_id, memory)

    def _form_memories(self, agent: Agent, percept) -> None:
        """Record this-tick perceived events into the agent's memory (if it has one).
        Only events emitted on the current tick are recorded, so the recency window
        doesn't create duplicates across ticks."""
        memory = getattr(agent, "memory", None)
        relationships = getattr(agent, "relationships", None)
        if memory is None or not hasattr(memory, "add"):
            return
        for event in percept.events:
            if event.tick == self.world.tick:
                memory.add(
                    MemoryItem(
                        text=describe_event(event),
                        ts=self.world.sim_time,
                        salience=event.salience,
                    )
                )
                if relationships is not None:
                    relationships.adjust(event.source_id, sentiment_for(event.kind))

    def _maybe_deliberate(self, agent_id: str, brain: Brain, percept) -> None:
        """Wake an LLM agent's deliberative layer when it perceives a salient event,
        subject to a per-agent cooldown. Proactive reaction, dispatched off-tick."""
        if getattr(brain, "provider", None) is None or not percept.events:
            return  # only LLM-backed brains deliberate
        top = max(percept.events, key=lambda e: e.salience)
        if top.salience < self.deliberate_threshold:
            return
        last = self._last_deliberation.get(agent_id, float("-inf"))
        if self.world.sim_time - last < self.deliberate_cooldown:
            return
        self._last_deliberation[agent_id] = self.world.sim_time
        self._metrics["deliberations"] += 1
        self.dispatch_converse(
            agent_id, f"You witnessed: {describe_event(top)}. React briefly, in character."
        )

    def _maybe_npc_converse(self) -> None:
        """Advance active NPC↔NPC conversations and matchmake new ones between nearby
        idle LLM agents. Off by default; enable with npc_chat=True."""
        if not self.npc_chat:
            return
        now = self.world.sim_time
        for convo in list(self._npc_convos):
            convo.tick(now)
            if convo.done:
                self._npc_convos.remove(convo)
                self._npc_chat_cooldown_until[frozenset((convo.a, convo.b))] = (
                    now + self.npc_chat_cooldown
                )
        busy = {agent_id for convo in self._npc_convos for agent_id in (convo.a, convo.b)}
        llm_ids = [aid for aid, brain in self.brains.items() if getattr(brain, "provider", None)]
        for i, a_id in enumerate(llm_ids):
            if a_id in busy:
                continue
            a = self.world.try_get(a_id)
            if not isinstance(a, Agent):
                continue
            for b_id in llm_ids[i + 1:]:
                if b_id in busy:
                    continue
                b = self.world.try_get(b_id)
                if not isinstance(b, Agent) or b.zone != a.zone:
                    continue
                if a.position.distance_to(b.position) > self._sense_radius(self.brains[a_id]):
                    continue
                if now < self._npc_chat_cooldown_until.get(frozenset((a_id, b_id)), float("-inf")):
                    continue
                self._npc_convos.append(
                    NpcConversation(self, a_id, b_id, self.npc_chat_turns, self.npc_chat_interval)
                )
                busy.update((a_id, b_id))
                break

    def _maybe_decay(self) -> None:
        """Periodically decay every agent's memory off the hot path."""
        if self.world.tick % self.memory_decay_every != 0:
            return
        elapsed = self.dt * self.memory_decay_every
        for agent_id in self.brains:
            agent = self.world.try_get(agent_id)
            memory = getattr(agent, "memory", None)
            if memory is not None and hasattr(memory, "decay"):
                memory.decay(elapsed)

    def step(self) -> None:
        """One tick: drain off-tick results, then perceive -> decide -> apply, then advance."""
        self.drain_results()
        self._apply_schedules()  # phase-driven goals before agents decide
        # Build the spatial index once per tick so each agent's perception is ~O(1).
        index = SpatialIndex(self.world.all(), cell_size=DEFAULT_SENSE_RADIUS)
        for agent_id, brain in self.brains.items():
            agent = self.world.try_get(agent_id)
            if not isinstance(agent, Agent):
                continue
            percept = perceive(self.world, agent, self._sense_radius(brain), index=index)
            action = brain.decide(agent, percept)
            self._apply(agent, action)
            self._form_memories(agent, percept)
            self._maybe_deliberate(agent_id, brain, percept)
        self._maybe_reflect()
        self._maybe_npc_converse()
        self.world.advance(self.dt)
        self._maybe_persist()
        self._maybe_decay()

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
