# Changelog

All notable changes to SYNK are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/); this project aims for [SemVer](https://semver.org/).

## [Unreleased]

### Security
- Session tokens are now validated on every post-join intent (`move`/`say`/`interact`/`leave`)
  via `AuthManager.is_for`; missing/forged tokens return `error: unauthorized`.
- CORS middleware + WebSocket Origin allowlist (`ALLOWED_ORIGINS`) and per-connection
  token-bucket rate limiting.
- Protocol version enforced (`unsupported_version`).

### Added
- **Live hybrid brain**: demo NPCs use `LLMBrain` (Mock with no key); per-agent `MemoryStore`
  and conversation history feed the LLM prompt.
- **Memory formation + decay** from perceived events each tick.
- **agent_event / dialogue broadcasting** to clients (positions, emotes, gifts, off-tick speech).
- **Persistence wired into the server** (`SYNK_DB_PATH`): world + memories load on boot and
  survive restarts.
- **Overhearing**: nearby non-addressed players hear NPC replies (`overheard: true`).
- **Proactive NPCs**: event-driven deliberation when a salient event is perceived.
- **Goal pursuit**: an LLM-set `set_goal` drives reactive movement toward the named target.
- **Autonomous NPC↔NPC conversations** (proximity-matchmade, bounded, overheard).
- **Spatial hash index** for ~O(1) perception; per-zone snapshot reuse in broadcasts.
- Examples: `remembers_you.py` (recall demo). Docker (`docker compose up`), GitHub Actions CI,
  Vitest client tests, PyPI metadata, npm-publishable `synk-sdk`.

## [0.1.0]

- Initial release: world/perception/A* pathfinding/memory; hybrid ReactiveBrain + LLMBrain with
  guarded Mock/Anthropic/OpenAI providers; dialogue, persistence, auth, fixed-timestep
  Simulation; FastAPI WebSocket server; TypeScript SDK + Three.js tavern demo. 207 tests.
