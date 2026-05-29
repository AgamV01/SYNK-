"""Brain contract and the action vocabulary agents act through.

Actions are immutable value objects. The reactive layer produces the cheap ones
(idle/wander/move_to/face/emote) synchronously every tick; the deliberative layer
may additionally produce give_item/set_goal/handoff (see task 41)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from ..geometry import Vec3


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


Action = Idle | Wander | MoveTo | Face | Emote
