# protocol/messages.md

Authoritative WebSocket message contract for SYNK. The Python server and the TypeScript SDK implement exactly what is written here. Derived from spec section 6.

All messages are JSON objects. Every message carries:
- `type` — a string tag identifying the message.
- `v` — an integer protocol version. Current version: `1`.

Coordinates are `[x, y, z]` arrays of three floats. `y` is up; spatial queries (range, overhearing) use the xz-plane only.

## Client → server

The player's client sends *intents*. The server is authoritative and may reject or clamp them.

### `join`
Sent once on connect. The server replies with `welcome` (which carries the session token).

Fields:
- `name` (string) — display name for the player.
- `zone` (string, optional) — preferred starting zone; server default if omitted.

```json
{ "type": "join", "v": 1, "name": "Ada", "zone": "tavern" }
```

### `move`
Update the player's position (and optionally facing). Sent at the client's input rate.

Fields:
- `position` (`[x, y, z]`) — requested world position.
- `facing` (number, optional) — yaw in radians (see Facing below).

```json
{ "type": "move", "v": 1, "position": [1.0, 0.0, -3.5], "facing": 1.5708 }
```

### `say`
Speak to a specific agent. Triggers the agent's deliberative (LLM) layer off-tick.

Fields:
- `target` (string) — id of the agent being addressed.
- `text` (string) — the player's utterance.

```json
{ "type": "say", "v": 1, "target": "npc_barkeep", "text": "What's on tap?" }
```

### `interact`
A non-verbal interaction directed at an agent.

Fields:
- `target` (string) — id of the agent.
- `kind` (string) — interaction kind, e.g. `"give_item"`, `"inspect"`.
- `payload` (object, optional) — kind-specific data, e.g. `{ "item": "coin" }`.

```json
{ "type": "interact", "v": 1, "target": "npc_barkeep", "kind": "give_item", "payload": { "item": "coin" } }
```

### `leave`
Voluntary disconnect. The server also handles abrupt socket close as an implicit leave.

```json
{ "type": "leave", "v": 1 }
```
