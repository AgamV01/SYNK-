# SYNK — Release-Readiness Review

Reviewer pass over the SYNK repo. All figures below were verified by running the
commands in the same session (see the pasted evidence in the PR/turn that added this file).

## (a) Verified final-state stats

| Metric | Value | How verified |
| --- | --- | --- |
| Commits on `main` | **149** | `git rev-list --count HEAD` |
| Python tests | **209 passed** | `pytest` (18 test files under `server/tests/`) |
| Client tests | **4 passed** | `npm test` (Vitest) |
| Coverage (`synk`) | **94%** (94.16% at the gate; threshold 80%) | `pytest --cov=synk --cov-fail-under=80` |
| LOC — `server/synk` | **2,375** Python | `find … -name '*.py' \| xargs wc -l` |
| LOC — `server/tests` | **2,318** Python | same |
| LOC — `client/src` | **1,003** TypeScript | same |
| Build | client `tsc --noEmit` clean; `vite build` + `build:sdk` OK | `npm run build` / `build:sdk` |
| Worktree | clean; `.gitignore` covers all artifacts | `git status` / `git clean -nd` (empty) |

## (b) Drift between PROGRESS.md and actual state

PROGRESS.md is an accurate journal **of the original 120-task v1 build** and ends at
"task 120 FINAL INTEGRATION GATE … 207 passed, 93.43% … All 120 fix_plan boxes checked.
SYNK v1 complete." It does **not** record the later release-readiness roadmap (security
hardening, wiring the dormant memory/persistence/overhearing layers, proactive + NPC↔NPC
deliberation, spatial index, CI/Docker/packaging), which was tracked in the plan file and
`CHANGELOG.md` ([Unreleased]) instead. Concretely:

- Commits: PROGRESS implies ~120; actual is **149**.
- Tests: PROGRESS says **207**; actual is **209**.
- Coverage: PROGRESS says **93.43%**; actual is **94%**.
- README badges still hard-code `tests: 207` / `coverage: 93%` — **stale** (fixed in the
  README-polish commit).
- `CLAUDE.md` references an "Everything Claude Code (ECC)" toolchain (planner agents,
  build-fixer, ralph-loop plugin). The loop actually ran in-session without those plugins;
  this is aspirational/doc drift, not a code issue.

No drift found between code and the protocol contract (`protocol/messages.md`) or between the
Python and TypeScript message shapes.

## (c) Loose ends / polish opportunities (found, NOT fixed — out of cleanup scope)

1. **Unbounded event buffer.** `World._events` is append-only and never pruned
   (`server/synk/world.py`). Fine for the demo and tests; a long-running server would grow
   memory over time. A ring buffer / periodic prune is the clean fix (behavioral change →
   out of cleanup scope).
2. **Restart loses obstacle-aware navigation.** When agents are restored from SQLite,
   `server/synk/server.py:_attach_brains_and_memory` registers a grid-less `ReactiveBrain`,
   so reloaded NPCs steer straight rather than via A* (obstacles aren't persisted).
3. **Voice STT unwired.** `client/src/demo/voice.ts` implements TTS (used) and STT
   (`startListening`), but no UI control invokes STT. Intentional (feature-flagged), worth a
   note/button later.
4. **Provider coverage 72%.** `server/synk/brains/providers.py` — the real Anthropic/OpenAI
   `generate` branches are unreachable without the SDKs/keys (guarded by design), so they're
   uncovered. Acceptable; could add monkeypatched tests.
5. **No live end-to-end loop test.** The running sim + broadcaster delivering *autonomous*
   dialogue over a real socket is exercised only in pieces (handler, broadcaster, sim each
   tested separately). An integration test over `TestClient(create_app(demo=True))` would
   close the gap.
6. **Static README badges** will drift again unless generated from CI (e.g., a coverage
   badge action).

None of the above are release blockers.

## (d) Release-readiness verdict

**🟢 GREEN.** All gates pass (209 tests, 94% coverage), the WebSocket server is
security-hardened (token auth, Origin allowlist, rate limiting, version checks), and CI,
Docker, and PyPI/npm packaging are in place with a clean worktree; the only remaining items
are minor, non-blocking polish (event-buffer pruning, restart-time pathfinding).
