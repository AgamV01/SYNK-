"""Apply chosen actions to the world, producing the WorldEvents that surface to
clients as `agent_event` messages (see protocol/messages.md)."""

from __future__ import annotations

from .brains.base import Action, Emote, GiveItem, Handoff, MoveTo, SetGoal
from .memory import score_event_salience
from .world import Agent, World, WorldEvent


def _event(agent: Agent, world: World, kind: str, payload: dict) -> WorldEvent:
    return WorldEvent(
        kind=kind,
        source_id=agent.id,
        zone=agent.zone,
        tick=world.tick,
        position=agent.position,
        salience=score_event_salience(kind),
        payload=payload,
    )


def apply_action(world: World, agent: Agent, action: Action) -> WorldEvent | None:
    """Mutate the agent for `action` and emit the matching WorldEvent (if any).

    Returns the emitted event, or None for actions that produce no broadcastable
    event (e.g. idle/wander/face — those only set the agent's action label)."""
    if isinstance(action, MoveTo):
        agent.current_action = "move_to"
        event = _event(agent, world, "moved", {"to": action.target.to_list()})
    elif isinstance(action, Emote):
        agent.current_action = action.emote
        event = _event(agent, world, "emoted", {"emote": action.emote})
    elif isinstance(action, GiveItem):
        agent.current_action = "give_item"
        event = _event(agent, world, "gave_item", {"item": action.item, "to": action.to_id})
    elif isinstance(action, SetGoal):
        agent.goal = action.goal
        agent.current_action = "set_goal"
        event = _event(agent, world, "goal_changed", {"goal": action.goal})
    elif isinstance(action, Handoff):
        agent.current_action = "handoff"
        event = _event(agent, world, "handoff", {"to": action.to_id, "topic": action.topic})
    else:
        return None
    world.emit_event(event)
    return event
