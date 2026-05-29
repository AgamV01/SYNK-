# Writing a custom brain

A *brain* decides what an agent does. SYNK ships two — `ReactiveBrain` (cheap, every
tick) and `LLMBrain` (hybrid) — but any object satisfying the `Brain` protocol works.

## The contract

From `synk.brains.base`:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Brain(Protocol):
    def decide(self, agent: Agent, percept: Percept) -> Action: ...
    async def converse(self, agent: Agent, percept: Percept, utterance: str) -> ConverseResult: ...
```

- **`decide`** is the hot path. It runs **every tick**, must be **synchronous**, and must
  do **no I/O** (no network, no disk, no `await`). Return an `Action`
  (`Idle`, `Wander`, `MoveTo`, `Face`, `Emote`, `GiveItem`, `SetGoal`, `Handoff`).
- **`converse`** is the off-tick deliberative path. It is `async` and *may* call an LLM.
  Return a `ConverseResult(text, action=None)` — a line to speak plus an optional action.

> **Invariant:** never call an LLM (or any blocking I/O) from `decide`, and never `await`
> an LLM on the tick. The simulation dispatches `converse` as a background task and folds
> its result back in as events on a later tick.

## A minimal brain

```python
from synk.brains.base import ConverseResult, Idle, Wander

class SentryBrain:
    def decide(self, agent, percept):
        # Stand guard unless something is nearby.
        return Wander() if percept.nearby else Idle()

    async def converse(self, agent, percept, utterance):
        return ConverseResult(text="Halt. State your business.")
```

Register it with the simulation:

```python
sim.register("npc_sentry", SentryBrain())
```

## Reusing the reactive layer

A common pattern (this is exactly what `LLMBrain` does) is to delegate `decide` to a
`ReactiveBrain` and only customize `converse`:

```python
from synk.brains.reactive import ReactiveBrain

class MyBrain:
    def __init__(self):
        self.reactive = ReactiveBrain(grid=my_grid)

    def decide(self, agent, percept):
        return self.reactive.decide(agent, percept)

    async def converse(self, agent, percept, utterance):
        ...  # your dialogue logic
```

Attach a `MemoryStore` to an agent as `agent.memory` and the `LLMBrain` will fold recalled
memories into the prompt automatically (it is duck-typed).
