# CLAUDE.md — SYNK

Conventions and tooling. Read the relevant part only when about to write code in an area you have not touched.

## Architectural invariants (never violate)
- The LLM is never called on the per-tick path and never awaited on the tick. Off-tick async tasks only; results re-enter as events. This is the core cost property of the project.
- The server is authoritative. Clients send intents, render snapshots.
- `protocol/messages.md` is the shared contract. Python and TS must match it.
- Persistence is async/batched; the tick never blocks on disk.
- The repo runs with zero API keys (MockProvider + ReactiveBrain). Never make a key required.

## Tooling — use it
Prefer existing components over reinventing:
- Use planner / architect orchestrator agents to break a phase into steps before implementing.
- Use the Python and TypeScript language-expert skills for idiomatic code in each stack.
- Use a build-fixer command to clear type or build errors incrementally instead of hand-patching, when available.
- Use a checkpoint command to record a verified state at a task boundary, when available.
- Run the security scan before the final gate.
- The test-coverage rule (>= 80%) applies. Do not lower the coverage bar.
- Heed PreToolUse hooks that warn on debug/console statements; do not commit debug noise.

## Code conventions
- Python: type hints everywhere, `from __future__ import annotations`, dataclasses for value objects, async only where it touches I/O. Tests in `server/tests/`, pytest.
- TypeScript: strict mode, no `any` in the SDK, explicit return types on exported functions.
- Keep modules focused; split a file that grows past a few hundred lines.

## Verification discipline
A task is done only when its `verify:` command passes and the full suite is still green. Paste real command output into `PROGRESS.md`. Never paraphrase a result you did not run.
