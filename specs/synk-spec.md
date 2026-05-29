# SYNK — Spec (v1 = everything)

Authoritative. Where silent, take the simplest correct option and note it.

## 1. What this is
Open-source framework for intelligent, LLM-driven NPCs in web-based 3D worlds. Server-authoritative Python runtime drives behavior, memory, dialogue. TypeScript SDK + Three.js demo render the world and let a player walk up, talk, and interact in real time. Differentiator: the hybrid brain (cheap reactive layer every tick, LLM only on meaningful events). Promise: clone-and-run in a browser with no API key.

## 2. Non-negotiables
- LLM never called inside the per-tick loop, never awaited on the tick. Dialogue and reflection run off-tick; results inject back as events on a later tick.
- Server authoritative. Clients send intents, render snapshots. Never trust client-reported agent state.
- No hardcoded provider. Brain and provider both pluggable. Runs fully with no API key via mock provider + reactive brain.
- `protocol/messages.md` is the single shared contract; Python and TS must not drift.
- Persistence never blocks the tick.

## 3. Architecture
Per agent, per tick: perceive, remember, decide, act.
Layers: World (entities, zones, spatial queries, tick), Agent (personality, brain, memory, goals, current action), Perception (percept from world, sense radius, zone-scoped), Brain (cheap sync `decide` returning an action with no I/O; async `converse`/`deliberate` that may call an LLM and returns dialogue and/or a structured action), Memory (items with timestamp + salience, decay, recall = recent ∪ salient, persisted), Simulation (fixed-timestep loop default 10 Hz, decoupled from render, dispatches async LLM work, drains results into events), Server (FastAPI WebSocket; intents in, snapshots and events out).
Hybrid triggers for the deliberative layer: (1) a player utterance directed at the agent, (2) a perceived salient event over threshold, (3) a low-frequency per-agent reflection timer. The reactive layer drives everything else every tick: wander, steer toward a target, face an entity, navigate around obstacles via pathfinding, emote.

## 4. Feature scope (v1 includes all of this)
Core sim: geometry + xz spatial queries; world, entities, zones; perception with sense radius; reactive utility behavior + steering; grid-based A* pathfinding around static obstacles (not naive straight-line); memory with salience, decay, recall.
LLM intelligence: provider interface with MockProvider (zero-config default), guarded AnthropicProvider (when `ANTHROPIC_API_KEY` set), guarded OpenAIProvider (when `OPENAI_API_KEY` set), selection by env defaulting to Mock; LLMBrain hybrid split that degrades to reactive dialogue with no provider; structured actions from LLM output (a spoken line plus an optional structured action: move_to, give_item, emote, set_goal, handoff) parsed safely, malformed output falls back to speech-only and is logged and never crashes the tick; low-frequency reflection writing salient memories.
Conversation: dialogue manager with history (player-to-agent); multi-party NPC-to-NPC dialogue that nearby players overhear.
Server/platform: FastAPI WebSocket server implementing the protocol; auth via anonymous short-lived session tokens issued on join and scoped to a player (no passwords, no accounts in v1); persistence via SQLite, async/batched, world + memory survive restart, never blocking the tick; multi-zone as logical zones in one process (perception and broadcast zone-scoped) rather than distributed sharding.
Client: protocol types mirroring the contract; SDK with connect, auto-reconnect, typed handlers, send intents; Three.js scene (ground, props/obstacles, lighting); player controller (WASD + camera); NPC avatars (capsules, name labels, speech bubbles, emote animations); talk UI (proximity prompt, chat input to `say`, replies as bubbles, overhearing); agent-state debug panel (current action, goal, recent-memory peek) so the intelligence is legible; voice (browser-native Web Speech API TTS for NPC lines and STT for player input, feature-flagged off by default, demo works fully with it off).
Examples/docs: a tavern example world (a few NPCs with distinct personalities, props, obstacles); README with zero-config quickstart, mermaid architecture, hybrid-brain explanation, upgrade-to-LLM steps; docs for writing a custom brain and a custom structured action.

## 5. Repo layout
```
synk/
  README.md
  LICENSE                         # MIT
  .gitignore
  protocol/messages.md
  server/
    pyproject.toml                # Python 3.11+
    synk/
      geometry.py  world.py  agent.py  perception.py  memory.py  pathfinding.py
      brains/ base.py reactive.py llm.py providers.py
      dialogue.py  persistence.py  auth.py  simulation.py  server.py
    examples/ headless_demo.py  tavern.py
    tests/                        # pytest, coverage >= 80%
  client/
    package.json  tsconfig.json  index.html  vite.config.ts
    src/
      sdk/ types.ts client.ts index.ts
      demo/ main.ts scene.ts player.ts npc.ts ui.ts voice.ts
```
SDK stays engine-agnostic: the protocol is plain WebSocket JSON, so a native engine client could implement the same contract later.

## 6. Protocol
JSON messages, each with `type` and version `v`. Defined fully in `protocol/messages.md`; mirror in TS and Python.
Client to server: `join` (name, optional zone) returns a session token; `move` (position, optional facing); `say` (target agent id, text); `interact` (target agent id, kind, payload); `leave`.
Server to client: `welcome` (player id, session token, tick rate, zone snapshot); `world_state` (throttled per-zone snapshot: agent id, name, position, facing, current action label); `agent_event` (agent id, kind such as spoke/emoted/moved/gave-item, payload); `dialogue` (agent id, text, optional overheard flag); `error` (code, message).
`messages.md` also pins: snapshot throttle rate, "nearby" radius for overhearing, facing representation, and the `agent_event` kinds that structured actions surface as.

## 7. Tech choices (decided)
Python 3.11+, FastAPI, uvicorn, pytest + coverage, SQLite (`aiosqlite` or stdlib). TypeScript, Vite, three. Anthropic + OpenAI SDKs both guarded so the package imports without them; Mock is default. MIT. Single process; zones logical.

## 8. Assumptions (override by editing this file)
Web/Three.js demo target; name SYNK; auth is anonymous short-lived tokens not accounts; multi-zone is logical not distributed; voice is browser-native and feature-flagged; persistence is SQLite, async/batched, non-blocking. These pragmatic forms deliver the full feature surface while staying buildable and dependency-light; swapping in a distributed backend, real accounts, or hosted speech is a clean later change behind the same interfaces.
