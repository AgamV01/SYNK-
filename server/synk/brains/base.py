"""Brain contract and the action vocabulary agents act through.

Actions are immutable value objects. The reactive layer produces the cheap ones
(idle/wander/move_to/face/emote) synchronously every tick; the deliberative layer
may additionally produce give_item/set_goal/handoff (see task 41)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

from ..geometry import Vec3

if TYPE_CHECKING:
    from ..perception import Percept
    from ..world import Agent


@dataclass(frozen=True, slots=True)
class Idle:
    kind: ClassVar[str] = "idle"


@dataclass(frozen=True, slots=True)
class Wander:
    kind: ClassVar[str] = "wander"


@dataclass(frozen=True, slots=True)
class MoveTo:
    target: Vec3
    kind: ClassVar[str] = "move_to"


@dataclass(frozen=True, slots=True)
class Face:
    target_id: str
    kind: ClassVar[str] = "face"


@dataclass(frozen=True, slots=True)
class Emote:
    emote: str
    kind: ClassVar[str] = "emote"


@dataclass(frozen=True, slots=True)
class GiveItem:
    item: str
    to_id: str
    kind: ClassVar[str] = "give_item"


@dataclass(frozen=True, slots=True)
class SetGoal:
    goal: str
    kind: ClassVar[str] = "set_goal"


@dataclass(frozen=True, slots=True)
class Handoff:
    to_id: str
    topic: str
    kind: ClassVar[str] = "handoff"


Action = Idle | Wander | MoveTo | Face | Emote | GiveItem | SetGoal | Handoff


@dataclass
class Goal:
    """A structured intention an agent is pursuing. `description` is the human/LLM
    readable goal; `priority` orders competing goals; `done` marks completion."""

    description: str
    priority: float = 1.0
    created_ts: float = 0.0
    done: bool = False

    def complete(self) -> None:
        self.done = True


@dataclass(frozen=True, slots=True)
class ConverseResult:
    """The output of the deliberative layer: a spoken line plus an optional action."""

    text: str
    action: Action | None = None


@runtime_checkable
class Brain(Protocol):
    """An agent's decision-maker.

    `decide` is the hot path: synchronous, no I/O, called every tick. `converse`
    is off-tick: it may call an LLM and so is async; its result is injected back
    into the world as events on a later tick. An LLM must never be awaited from
    `decide`."""

    def decide(self, agent: Agent, percept: Percept) -> Action: ...

    async def converse(
        self, agent: Agent, percept: Percept, utterance: str
    ) -> ConverseResult: ...
