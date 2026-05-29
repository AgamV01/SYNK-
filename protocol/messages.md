# protocol/messages.md

Authoritative WebSocket message contract for SYNK. The Python server and the TypeScript SDK implement exactly what is written here. Derived from spec section 6.

All messages are JSON objects. Every message carries:
- `type` — a string tag identifying the message.
- `v` — an integer protocol version. Current version: `1`.

### Versioning
The `v` field is **required on every message in both directions**. A receiver that sees a `v` it does not support replies with an `error` of code `"unsupported_version"` and ignores the message. Within a major version, fields may only be *added* (receivers ignore unknown fields); removing or repurposing a field requires bumping `v`. Every message type documented below includes a concrete JSON example carrying `"v": 1`.

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

## Server → client

The server sends authoritative state and events. Clients render these; they never compute agent state locally.

### `welcome`
Reply to `join`. Carries the session token and an initial snapshot of the player's zone.

Fields:
- `player_id` (string) — id assigned to this player.
- `token` (string) — short-lived session token (see auth in spec section 4).
- `tick_rate` (number) — simulation ticks per second (default 10).
- `zone` (string) — the zone the player joined.
- `snapshot` (object) — same shape as a `world_state` body (`tick`, `agents`).

```json
{
  "type": "welcome", "v": 1,
  "player_id": "player_7f3a", "token": "eyJ...", "tick_rate": 10, "zone": "tavern",
  "snapshot": { "tick": 0, "agents": [] }
}
```

### `world_state`
Throttled per-zone snapshot of agents. See Snapshot throttle below.

Fields:
- `zone` (string) — zone these agents belong to.
- `tick` (number) — simulation tick the snapshot was taken at.
- `agents` (array) — each: `id` (string), `name` (string), `position` (`[x,y,z]`), `facing` (number, yaw radians), `action` (string label of current action, e.g. `"wander"`, `"approach"`, `"talk"`).

```json
{
  "type": "world_state", "v": 1, "zone": "tavern", "tick": 142,
  "agents": [
    { "id": "npc_barkeep", "name": "Gus", "position": [0.0, 0.0, 0.0], "facing": 0.0, "action": "wander" }
  ]
}
```

### `agent_event`
A discrete thing an agent did. `kind` is one of the enumerated kinds (see Structured-action event kinds).

Fields:
- `agent_id` (string) — the acting agent.
- `kind` (string) — event kind: `spoke`, `emoted`, `moved`, `gave_item`, `goal_changed`, `handoff`.
- `payload` (object) — kind-specific, e.g. `{ "emote": "wave" }` or `{ "item": "ale", "to": "player_7f3a" }`.

```json
{ "type": "agent_event", "v": 1, "agent_id": "npc_barkeep", "kind": "emoted", "payload": { "emote": "wave" } }
```

### `dialogue`
A line of speech from an agent. `overheard` is true when the line was not addressed to the receiving player but they are within the nearby radius (see Overhearing).

Fields:
- `agent_id` (string) — the speaking agent.
- `text` (string) — the spoken line.
- `overheard` (boolean, optional) — defaults to false.

```json
{ "type": "dialogue", "v": 1, "agent_id": "npc_barkeep", "text": "We've a fine stout tonight.", "overheard": false }
```

### `error`
Sent when the server rejects input or hits a recoverable problem.

Fields:
- `code` (string) — machine-readable code, e.g. `"bad_message"`, `"unknown_agent"`, `"unauthorized"`.
- `message` (string) — human-readable detail.

```json
{ "type": "error", "v": 1, "code": "unknown_agent", "message": "No agent with id 'npc_ghost' in zone 'tavern'." }
```

## Pinned parameters

These values are part of the contract; client and server must agree on them.

### Snapshot throttle
`world_state` is broadcast **at most 10 times per second** (every 100 ms), independent of the simulation tick rate. If the sim runs faster, snapshots are coalesced; if a zone is unchanged, the server may skip a broadcast. Clients must tolerate gaps and interpolate between snapshots.

### Nearby radius (overhearing)
The "nearby" radius for overhearing is **12.0 world units**, measured as xz-plane distance from the speaking agent. A `dialogue` message addressed to one player is also delivered to every other player within this radius with `overheard: true`. NPC↔NPC dialogue is delivered to all players within the radius, always with `overheard: true`.

### Facing
`facing` is a **yaw angle in radians**, a single float. `0.0` faces the `+x` axis; the angle increases counter-clockwise toward `+z` (right-handed, rotating about the `+y` up-axis). There is no pitch or roll in the protocol. Facing is optional on `move`; when omitted the server keeps the player's previous facing.

### Structured-action event kinds
LLM structured actions (spec section 4) surface to clients as `agent_event` messages with these `kind` values:

| structured action | `agent_event.kind` | payload |
| --- | --- | --- |
| (spoken line) | `spoke` | `{ "text": string }` (also sent as a `dialogue` message) |
| `emote` | `emoted` | `{ "emote": string }` |
| `move_to` | `moved` | `{ "to": [x,y,z] }` |
| `give_item` | `gave_item` | `{ "item": string, "to": string }` |
| `set_goal` | `goal_changed` | `{ "goal": string }` |
| `handoff` | `handoff` | `{ "to": string, "topic": string }` |

Malformed LLM output never produces an `agent_event`; it falls back to a speech-only `dialogue` and is logged server-side (spec section 4).
