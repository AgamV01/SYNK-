# fix_plan.md — SYNK v1 (120 tasks)

Work top to bottom. One unchecked task per Ralph iteration, topmost whose dependencies are checked. Run its `verify:` for real before checking the box; paste output into PROGRESS.md. Each task is one commit. Spec sections are in `specs/synk-spec.md`.

## Scaffolding & tooling
- [x] 1. git repo + MIT LICENSE. verify: `git rev-parse --git-dir && test -f LICENSE`
- [x] 2. .gitignore (Python + Node). verify: `grep -q __pycache__ .gitignore && grep -q node_modules .gitignore`
- [x] 3. Dir skeleton + empty module files per spec section 5. verify: `test -f server/synk/__init__.py && test -d client/src/sdk`
- [x] 4. server/pyproject.toml with deps + pytest/coverage config. verify: `cd server && python -c "import tomllib,pathlib;tomllib.loads(pathlib.Path('pyproject.toml').read_text())"`
- [x] 5. Installable package; import works. verify: `cd server && pip install -e . -q && python -c "import synk"`
- [x] 6. client/package.json (vite+three+typescript). verify: `cd client && node -e "require('./package.json')"`
- [x] 7. npm install. verify: `cd client && npm install && test -d node_modules`
- [x] 8. tsconfig strict + vite.config.ts; empty src type-checks. verify: `cd client && npx tsc --noEmit`
- [x] 9. README skeleton (title + section stubs). verify: `grep -qi synk README.md`

## Protocol contract
- [x] 10. messages.md: client->server messages documented with field shapes. verify: `grep -q '"type": "join"' protocol/messages.md`
- [x] 11. messages.md: server->client messages documented with field shapes. verify: `grep -q '"type": "world_state"' protocol/messages.md`
- [x] 12. messages.md: throttle rate, nearby radius, facing repr, structured-action event kinds. verify: `grep -qi throttle protocol/messages.md && grep -qi facing protocol/messages.md`
- [x] 13. messages.md: version field + a JSON example per message. verify: `grep -c '"v":' protocol/messages.md`

## Geometry
- [x] 14. Vec3 dataclass + add/sub/mul + test. verify: `cd server && pytest tests/test_geometry.py -q`
- [x] 15. Vec3 length, length_xz, normalize + test. verify: `cd server && pytest tests/test_geometry.py -q`
- [x] 16. Vec3 distance_to (xz), to/from list + test. verify: `cd server && pytest tests/test_geometry.py -q`

## World & entities
- [x] 17. Entity base (id, position, zone) + test. verify: `cd server && pytest tests/test_world.py -q`
- [x] 18. Player + Agent entity skeletons + test. verify: `cd server && pytest tests/test_world.py -q`
- [x] 19. World add/remove entity + test. verify: `cd server && pytest tests/test_world.py -q`
- [x] 20. World get-by-id, list-by-zone + test. verify: `cd server && pytest tests/test_world.py -q`
- [x] 21. World radius query (xz, zone-scoped) + test. verify: `cd server && pytest tests/test_world.py -q`
- [x] 22. World tick counter + sim time + test. verify: `cd server && pytest tests/test_world.py -q`

## Perception
- [x] 23. Percept dataclass (nearby entities, events) + test. verify: `cd server && pytest tests/test_perception.py -q`
- [x] 24. Build percept within sense radius + test. verify: `cd server && pytest tests/test_perception.py -q`
- [x] 25. Perception zone-scoping (exclude other zones) + test. verify: `cd server && pytest tests/test_perception.py -q`
- [x] 26. Recent perceivable events feed + test. verify: `cd server && pytest tests/test_perception.py -q`

## Pathfinding
- [x] 27. Grid from obstacle list + test. verify: `cd server && pytest tests/test_pathfinding.py -q`
- [x] 28. A* core (open/closed set, heuristic) + test. verify: `cd server && pytest tests/test_pathfinding.py -q`
- [x] 29. Straight path on empty grid + test. verify: `cd server && pytest tests/test_pathfinding.py -q`
- [x] 30. Path around an obstacle + test. verify: `cd server && pytest tests/test_pathfinding.py -q`
- [x] 31. Waypoint simplification + test. verify: `cd server && pytest tests/test_pathfinding.py -q`
- [x] 32. No-path case returns empty + test. verify: `cd server && pytest tests/test_pathfinding.py -q`

## Memory
- [x] 33. MemoryItem dataclass (text, ts, salience) + test. verify: `cd server && pytest tests/test_memory.py -q`
- [x] 34. Memory store add + capacity cap + test. verify: `cd server && pytest tests/test_memory.py -q`
- [x] 35. Salience scoring helper + test. verify: `cd server && pytest tests/test_memory.py -q`
- [x] 36. Decay over time + test. verify: `cd server && pytest tests/test_memory.py -q`
- [x] 37. Recall recent N + test. verify: `cd server && pytest tests/test_memory.py -q`
- [x] 38. Recall top-salient K + test. verify: `cd server && pytest tests/test_memory.py -q`
- [x] 39. Recall union + dedupe + ordering + test. verify: `cd server && pytest tests/test_memory.py -q`

## Brain interface & actions
- [x] 40. Action types: idle, wander, move_to, face, emote + test. verify: `cd server && pytest tests/test_brain_contract.py -q`
- [x] 41. Action types: give_item, set_goal, handoff + test. verify: `cd server && pytest tests/test_brain_contract.py -q`
- [x] 42. Brain Protocol (sync decide, async converse) + dummy-brain test. verify: `cd server && pytest tests/test_brain_contract.py -q`
- [x] 43. Goal representation + test. verify: `cd server && pytest tests/test_brain_contract.py -q`

## Reactive brain
- [x] 44. Idle/wander selection + test. verify: `cd server && pytest tests/test_reactive.py -q`
- [x] 45. Detect nearby player -> approach + test. verify: `cd server && pytest tests/test_reactive.py -q`
- [x] 46. Steering toward target using path + test. verify: `cd server && pytest tests/test_reactive.py -q`
- [x] 47. Face entity + test. verify: `cd server && pytest tests/test_reactive.py -q`
- [x] 48. Templated greeting dialogue (converse) + test. verify: `cd server && pytest tests/test_reactive.py -q`
- [x] 49. Utility scoring to choose behavior + test. verify: `cd server && pytest tests/test_reactive.py -q`
- [x] 50. Emote on event + test. verify: `cd server && pytest tests/test_reactive.py -q`

## Headless sanity
- [x] 51. examples/headless_demo.py: spawn agents, N ticks, tick log, --selftest. verify: `cd server && python examples/headless_demo.py --selftest`
- [x] 52. Headless: agent navigates around an obstacle (assert path). verify: `cd server && python examples/headless_demo.py --selftest`
- [x] 53. Headless: agent reacts to scripted nearby player (assert greeting). verify: `cd server && python examples/headless_demo.py --selftest`

## LLM providers
- [x] 54. Provider interface (generate) + test. verify: `cd server && pytest tests/test_providers.py -q`
- [x] 55. MockProvider context-flavored lines + test. verify: `cd server && pytest tests/test_providers.py -q`
- [x] 56. Provider selection by env, default Mock, no keys. verify: `cd server && pytest tests/test_providers.py -q` (must pass with no keys set)
- [x] 57. Guarded AnthropicProvider (no crash without sdk/key) + test. verify: `cd server && pytest tests/test_providers.py -q`
- [x] 58. Guarded OpenAIProvider + test. verify: `cd server && pytest tests/test_providers.py -q`
- [x] 59. Prompt builder (personality + memory + conversation) + test. verify: `cd server && pytest tests/test_providers.py -q`

## LLM brain
- [x] 60. LLMBrain.decide delegates to reactive, no I/O + test. verify: `cd server && pytest tests/test_llm_brain.py -q`
- [x] 61. LLMBrain.converse via provider + test. verify: `cd server && pytest tests/test_llm_brain.py -q`
- [x] 62. LLMBrain degrades to reactive dialogue without provider + test. verify: `cd server && pytest tests/test_llm_brain.py -q`
- [x] 63. Conversation-context assembly for converse + test. verify: `cd server && pytest tests/test_llm_brain.py -q`

## Structured actions
- [x] 64. Action schema for LLM output (JSON contract) + test. verify: `cd server && pytest tests/test_structured_actions.py -q`
- [x] 65. Safe parse of LLM structured output + test. verify: `cd server && pytest tests/test_structured_actions.py -q`
- [x] 66. Malformed output -> speech-only fallback + log, no raise + test. verify: `cd server && pytest tests/test_structured_actions.py -q`
- [x] 67. Apply parsed action (move_to, emote) + test. verify: `cd server && pytest tests/test_structured_actions.py -q`
- [x] 68. Apply parsed action (give_item, set_goal, handoff) + test. verify: `cd server && pytest tests/test_structured_actions.py -q`

## Reflection
- [x] 69. Reflection timer scheduling (low freq, per-agent) + test. verify: `cd server && pytest tests/test_reflection.py -q`
- [x] 70. Reflection summarizes recent memory -> salient memory + test. verify: `cd server && pytest tests/test_reflection.py -q`
- [x] 71. Reflection runs off-tick (async) + test. verify: `cd server && pytest tests/test_reflection.py -q`

## Dialogue
- [x] 72. Conversation object + history + test. verify: `cd server && pytest tests/test_dialogue.py -q`
- [x] 73. DialogueManager start/route player->agent + test. verify: `cd server && pytest tests/test_dialogue.py -q`
- [x] 74. DialogueManager append turns, fetch history + test. verify: `cd server && pytest tests/test_dialogue.py -q`
- [x] 75. Multi-party NPC->NPC conversation + test. verify: `cd server && pytest tests/test_dialogue.py -q`
- [x] 76. Overhearing: nearby players receive dialogue (flag) + test. verify: `cd server && pytest tests/test_dialogue.py -q`

## Persistence
- [x] 77. SQLite schema + migrate on boot + test. verify: `cd server && pytest tests/test_persistence.py -q`
- [x] 78. Async/batched writer (queue, flush) + test. verify: `cd server && pytest tests/test_persistence.py -q`
- [x] 79. Save world snapshot + test. verify: `cd server && pytest tests/test_persistence.py -q`
- [x] 80. Load world snapshot on boot + test. verify: `cd server && pytest tests/test_persistence.py -q`
- [x] 81. Save/load agent memory roundtrip + test. verify: `cd server && pytest tests/test_persistence.py -q`
- [x] 82. Persistence write stays off the tick path + test. verify: `cd server && pytest tests/test_persistence.py -q`

## Auth
- [x] 83. Issue anonymous short-lived session token + test. verify: `cd server && pytest tests/test_auth.py -q`
- [x] 84. Validate token + expiry + test. verify: `cd server && pytest tests/test_auth.py -q`
- [x] 85. Token scoped to player id + test. verify: `cd server && pytest tests/test_auth.py -q`

## Simulation loop
- [x] 86. Fixed-timestep loop scaffold (start/stop, dt) + test. verify: `cd server && pytest tests/test_simulation.py -q`
- [x] 87. Per-tick perceive -> decide -> apply action + test. verify: `cd server && pytest tests/test_simulation.py -q`
- [x] 88. Async LLM dispatch queue off-tick + test. verify: `cd server && pytest tests/test_simulation.py -q`
- [x] 89. Drain completed LLM results into world events + test. verify: `cd server && pytest tests/test_simulation.py -q`
- [x] 90. Invariant test: no LLM call on the tick path (assert). verify: `cd server && pytest tests/test_simulation.py -q`
- [x] 91. Wire reflection + persistence hooks into loop + test. verify: `cd server && pytest tests/test_simulation.py -q`

## Server
- [x] 92. FastAPI app + /healthz + test. verify: `cd server && pytest tests/test_server.py -q`
- [x] 93. WS accept; join -> welcome + token + test. verify: `cd server && pytest tests/test_server.py -q`
- [x] 94. WS move intent updates player + test. verify: `cd server && pytest tests/test_server.py -q`
- [x] 95. WS say intent -> dialogue event + test. verify: `cd server && pytest tests/test_server.py -q`
- [x] 96. WS interact intent -> agent_event + test. verify: `cd server && pytest tests/test_server.py -q`
- [x] 97. WS world_state broadcast (throttled, zone-scoped) + test. verify: `cd server && pytest tests/test_server.py -q`
- [x] 98. WS leave/disconnect cleanup + test. verify: `cd server && pytest tests/test_server.py -q`
- [x] 99. WS error message on bad input + test. verify: `cd server && pytest tests/test_server.py -q`
- [x] 100. E2E WS test: join, move, say, receive welcome+state+dialogue. verify: `cd server && pytest tests/test_e2e_ws.py -q`

## TypeScript SDK
- [x] 101. sdk/types.ts mirrors protocol. verify: `cd client && npx tsc --noEmit`
- [x] 102. sdk/client.ts connect + typed event emitter. verify: `cd client && npx tsc --noEmit`
- [x] 103. sdk/client.ts send intents (join/move/say/interact/leave). verify: `cd client && npx tsc --noEmit`
- [x] 104. sdk/client.ts auto-reconnect + backoff. verify: `cd client && npx tsc --noEmit`
- [x] 105. sdk/index.ts exports. verify: `cd client && npx tsc --noEmit`

## Three.js demo
- [x] 106. scene.ts ground + lighting + props/obstacles. verify: `cd client && npm run build`
- [x] 107. player.ts WASD + camera, emits move. verify: `cd client && npm run build`
- [x] 108. npc.ts avatars from world_state + name labels. verify: `cd client && npm run build`
- [x] 109. npc.ts speech bubbles + emote animation. verify: `cd client && npm run build`
- [x] 110. ui.ts proximity prompt + chat input -> say. verify: `cd client && npm run build`
- [x] 111. ui.ts overhearing display. verify: `cd client && npm run build`
- [ ] 112. ui.ts agent-state debug panel (action, goal, memory). verify: `cd client && npm run build`
- [ ] 113. voice.ts Web Speech TTS + STT, flagged off by default. verify: `cd client && npm run build`
- [ ] 114. main.ts wire SDK + scene + ui; connect to server. verify: `cd client && npm run build`

## Example, docs, final gates
- [ ] 115. examples/tavern.py: zone, props/obstacles, 3 NPCs with personalities + --selftest. verify: `cd server && python examples/tavern.py --selftest`
- [ ] 116. README: zero-config quickstart + exact run steps. verify: follow the quickstart on a clean checkout; paste the command sequence.
- [ ] 117. README: mermaid architecture + hybrid-brain section + upgrade-to-LLM. verify: `grep -qi mermaid README.md && grep -qi hybrid README.md`
- [ ] 118. docs/writing-a-brain.md + docs/custom-actions.md. verify: `test -f docs/writing-a-brain.md && test -f docs/custom-actions.md`
- [ ] 119. Coverage gate >= 80%. verify: `cd server && pytest --cov=synk --cov-fail-under=80`
- [ ] 120. Final integration gate: security scan clean, then server cov + client tsc + build all green. verify: run the security scan, then `cd server && pytest --cov=synk --cov-fail-under=80 && cd ../client && npx tsc --noEmit && npm run build`

When every box is checked and task 120 is green in the same iteration, emit `<promise>SYNK_V1_COMPLETE</promise>`.
