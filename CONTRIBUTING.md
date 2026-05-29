# Contributing to SYNK

Thanks for your interest! SYNK is a Python runtime + TypeScript SDK + Three.js demo for
LLM-driven NPCs. This guide gets you productive fast.

## Dev setup

**Server (Python 3.11+):**

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest --cov=synk --cov-fail-under=80   # full suite + coverage gate
```

**Client (Node 18+):**

```bash
cd client
npm install
npm test          # Vitest
npm run build     # tsc --noEmit + vite build
npm run build:sdk # emit the publishable SDK to dist-sdk/
```

Run the whole thing: see the [Quickstart](README.md#quickstart) (or `docker compose up --build`).

## Conventions (please follow)

- **Every change is one small, tested, green increment.** Add/extend a test with each change;
  keep server coverage **≥ 80%** (`pytest --cov=synk --cov-fail-under=80`).
- **Architectural invariants** (see `CLAUDE.md`):
  - The LLM is **never** called on the per-tick path and never awaited on the tick. Deliberation
    runs off-tick via `Simulation.dispatch_converse`; results re-enter as events.
  - The server is authoritative; clients send intents and render snapshots.
  - `protocol/messages.md` is the single source of truth — change Python **and** TypeScript
    **and** the doc together.
  - Persistence is async/batched; never block the tick on disk.
  - The package runs with **zero API keys** (MockProvider + reactive brain) — never make a key
    required.
- **Python:** type hints everywhere, `from __future__ import annotations`, dataclasses for value
  objects. **TypeScript:** strict mode, no `any` in the SDK.
- Extend a brain or action? See [docs/writing-a-brain.md](docs/writing-a-brain.md) and
  [docs/custom-actions.md](docs/custom-actions.md).

## Pull requests

1. Fork and branch from `main`.
2. Make your change with tests; ensure `pytest`, `npm test`, `tsc`, and `npm run build` all pass
   (CI runs these on every PR).
3. Update `protocol/messages.md` and `CHANGELOG.md` if behavior/protocol changed.
4. Open a PR describing the *why*. Keep it focused.

By contributing you agree your work is licensed under the project's [MIT License](LICENSE).
