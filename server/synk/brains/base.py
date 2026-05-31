"""Brain contract and the action vocabulary agents act through.

Actions are immutable value objects. The reactive layer produces the cheap ones
(idle/wander/move_to/face/emote) synchronously every tick; the deliberative layer
may additionally produce give_item/set_goal/handoff (see task 41)."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

from ..geometry import Vec3

logger = logging.getLogger("synk.brains")

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


# JSON contract the LLM is asked to follow for an optional structured action.
# The model returns an object like:
#   {"speech": "...", "action": {"type": "move_to", "target": [x, y, z]}}
# `action` may be null/omitted (speech-only). Recognized action objects:
ACTION_SCHEMA: dict[str, list[str]] = {
    "move_to": ["target"],     # target: [x, y, z]
    "face": ["target_id"],     # target_id: str
    "emote": ["emote"],        # emote: str
    "give_item": ["item", "to"],   # item: str, to: agent/player id
    "set_goal": ["goal"],      # goal: str
    "handoff": ["to", "topic"],    # to: agent id, topic: str
}


# Human/LLM-readable descriptions and per-field JSON-schema fragments, used to build
# native tool-calling schemas from ACTION_SCHEMA without duplicating the field list.
_ACTION_DESCRIPTIONS: dict[str, str] = {
    "move_to": "Walk to a world position [x, y, z].",
    "face": "Turn to face another entity by id.",
    "emote": "Play a short emote/gesture (e.g. wave, nod, shrug).",
    "give_item": "Hand an item to another agent or player.",
    "set_goal": "Adopt a short-term goal to pursue.",
    "handoff": "Hand the conversation to another agent on a topic.",
}
_FIELD_SCHEMA: dict[str, dict] = {
    "target": {
        "type": "array",
        "items": {"type": "number"},
        "minItems": 3,
        "maxItems": 3,
        "description": "World position [x, y, z].",
    },
    "target_id": {"type": "string", "description": "Id of the entity to face."},
    "emote": {"type": "string", "description": "Emote/gesture name."},
    "item": {"type": "string", "description": "Item name."},
    "to": {"type": "string", "description": "Recipient agent/player id."},
    "goal": {"type": "string", "description": "Goal description."},
    "topic": {"type": "string", "description": "Conversation topic."},
}


def action_tool_schemas() -> list[dict]:
    """Build provider-agnostic (Anthropic-style) tool definitions from ACTION_SCHEMA.

    Each entry is `{"name", "description", "input_schema"}`. OpenAIProvider translates
    these into its own function-tool format; AnthropicProvider passes them through.
    The single source of truth for fields stays ACTION_SCHEMA."""
    tools: list[dict] = []
    for name, fields in ACTION_SCHEMA.items():
        properties = {field: _FIELD_SCHEMA[field] for field in fields}
        tools.append(
            {
                "name": name,
                "description": _ACTION_DESCRIPTIONS.get(name, f"Perform the {name} action."),
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": list(fields),
                },
            }
        )
    return tools


def tool_call_to_output(name: str, tool_input: Mapping, speech: str = "") -> str:
    """Serialize a native tool-call (name + input) into the action-JSON string that
    `parse_llm_output` understands, so the tool-calling and text paths converge."""
    return json.dumps({"speech": speech, "action": {"type": name, **dict(tool_input)}})


def action_from_dict(data: dict) -> Action:
    """Map a structured-action JSON object to a typed Action.

    Raises ValueError on an unknown type or a missing/ill-typed field."""
    kind = data.get("type")
    try:
        if kind == "move_to":
            return MoveTo(target=Vec3.from_list(data["target"]))
        if kind == "face":
            return Face(target_id=str(data["target_id"]))
        if kind == "emote":
            return Emote(emote=str(data["emote"]))
        if kind == "give_item":
            return GiveItem(item=str(data["item"]), to_id=str(data["to"]))
        if kind == "set_goal":
            return SetGoal(goal=str(data["goal"]))
        if kind == "handoff":
            return Handoff(to_id=str(data["to"]), topic=str(data["topic"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"malformed action object for type {kind!r}: {exc}") from exc
    raise ValueError(f"unknown action type: {kind!r}")


def _extract_json_object(text: str) -> dict | None:
    """Pull a JSON object out of `text`, tolerating prose or ``` fences around it."""
    text = text.strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def parse_llm_output(text: str) -> tuple[str, Action | None]:
    """Safely parse an LLM reply into (speech, optional action).

    Never raises. If the output is not the expected JSON, the whole text becomes
    the spoken line and the action is None. A malformed action object is dropped
    (logged) and degrades to speech-only — so bad model output can't crash a tick."""
    data = _extract_json_object(text)
    if data is None:
        return text.strip(), None
    speech = str(data.get("speech", "")).strip() or text.strip()
    action: Action | None = None
    action_obj = data.get("action")
    if isinstance(action_obj, dict):
        try:
            action = action_from_dict(action_obj)
        except ValueError:
            logger.warning("discarding malformed structured action: %r", action_obj)
            action = None
    return speech, action
