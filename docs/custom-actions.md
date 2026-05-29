# Adding a custom structured action

Actions are the vocabulary agents act through. They flow two ways:

1. A brain's `decide`/`converse` returns an `Action`.
2. The LLM emits a structured action as JSON, which is parsed into an `Action`.

Adding a new action takes three small, co-located changes. We'll add a `sit` action.

## 1. Define the action value object

In `synk/brains/base.py`, add a frozen dataclass with a `kind` label and extend the
`Action` union:

```python
@dataclass(frozen=True, slots=True)
class Sit:
    target_id: str
    kind: ClassVar[str] = "sit"

Action = Idle | Wander | MoveTo | Face | Emote | GiveItem | SetGoal | Handoff | Sit
```

## 2. Teach the LLM parser about it

So the LLM can request it, map its JSON object in `action_from_dict` (same file) and
document it in `ACTION_SCHEMA`:

```python
ACTION_SCHEMA["sit"] = ["target_id"]

# inside action_from_dict:
if kind == "sit":
    return Sit(target_id=str(data["target_id"]))
```

`parse_llm_output` already routes through `action_from_dict`, and malformed objects still
degrade safely to speech-only — no extra work.

## 3. Apply it to the world

In `synk/actions.py`, handle the new action in `apply_action` so it mutates the agent and
emits the matching `WorldEvent` (which surfaces to clients as an `agent_event`):

```python
elif isinstance(action, Sit):
    agent.current_action = "sit"
    event = _event(agent, world, "sat", {"on": action.target_id})
```

If clients should render it, add the new `agent_event.kind` (`"sat"`) to the table in
`protocol/messages.md` and handle it in the client (`client/src/demo/main.ts` /
`npc.ts`). Keep the Python and TypeScript sides in sync — `protocol/messages.md` is the
single source of truth.

## Checklist

- [ ] dataclass + `Action` union (base.py)
- [ ] `ACTION_SCHEMA` + `action_from_dict` (base.py)
- [ ] `apply_action` branch (actions.py)
- [ ] protocol doc + client handling (if player-visible)
- [ ] a test for each step
