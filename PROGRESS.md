# PROGRESS.md — SYNK build journal

Append-only. One entry per completed task. The next iteration reads the tail to orient, so keep entries concise and factual. Newest at the bottom.

Entry format:
## <date time> — task <N> <title>
verify: <exact command run>
result: <exact observed output, trimmed to relevant lines>
files: <paths created/modified>
notes: <only if you deviated from the spec or hit a gotcha>

---

## 2026-05-28 — env setup (prerequisite, not a task)
System Python is 3.9.6 (no tomllib). Provisioned Python 3.12.13 via `uv` into a repo-root venv at `.venv`. ALL server commands must run with `source .venv/bin/activate` first. uv is at ~/.local/bin/uv; node v24, npm 11.

## 2026-05-28 — task 1 git repo + MIT LICENSE
verify: `git rev-parse --git-dir && test -f LICENSE`
result: `.git` printed, TASK1_PASS. Repo + MIT LICENSE already present from initial commit.
files: fix_plan.md (checkbox), PROGRESS.md

## 2026-05-28 — task 2 .gitignore (Python + Node)
verify: `grep -q __pycache__ .gitignore && grep -q node_modules .gitignore`
result: TASK2_PASS
files: .gitignore (new), fix_plan.md, PROGRESS.md

## 2026-05-28 — task 3 dir skeleton + empty module files
verify: `test -f server/synk/__init__.py && test -d client/src/sdk`
result: TASK3_PASS. Created server/synk/{geometry,world,agent,perception,memory,pathfinding,dialogue,persistence,auth,simulation,server}.py, server/synk/brains/{base,reactive,llm,providers}.py, examples/, tests/, client/src/{sdk,demo}/*.ts — all empty per spec section 5.
files: 28 empty module files (new), fix_plan.md, PROGRESS.md

## 2026-05-28 — task 4 server/pyproject.toml
verify: `cd server && python -c "import tomllib,pathlib;tomllib.loads(pathlib.Path('pyproject.toml').read_text())"`
result: TASK4_PASS. setuptools build backend; deps fastapi/uvicorn/aiosqlite; optional [llm]=anthropic,openai (guarded) and [dev]=pytest,pytest-asyncio,pytest-cov,httpx. pytest asyncio_mode=auto; coverage source=synk.
files: server/pyproject.toml (new), fix_plan.md, PROGRESS.md

## 2026-05-28 — task 5 installable package
verify: `cd server && pip install -e . -q && python -c "import synk"`
result: TASK5_PASS. Removed `readme = "../README.md"` from pyproject (setuptools forbids reading files outside project root). Also installed `.[dev]` extras → pytest 9.0.3 available.
files: server/pyproject.toml, fix_plan.md, PROGRESS.md
notes: pytest is 9.0.3 (very new); watch pytest-asyncio compatibility when async tests start (~task 71+).

## 2026-05-28 — task 6 client/package.json
verify: `cd client && node -e "require('./package.json')"`
result: TASK6_PASS. three ^0.160 dep; vite/typescript/@types/three dev. scripts: dev, build (tsc --noEmit && vite build), preview, typecheck.
files: client/package.json (new), fix_plan.md, PROGRESS.md

## 2026-05-28 — task 7 npm install
verify: `cd client && npm install && test -d node_modules`
result: TASK7_PASS. NOTE: user's ~/.npm cache has root-owned files (npm bug) → plain `npm install` fails EACCES. Workaround used: `npm install --cache /tmp/synk-npm-cache`. Future npm installs must use that flag (do NOT sudo chown the user's cache).
files: client/package-lock.json (new), node_modules/ (gitignored), fix_plan.md, PROGRESS.md

## 2026-05-28 — task 8 tsconfig strict + vite.config.ts
verify: `cd client && npx tsc --noEmit`
result: TASK8_PASS. tsconfig strict + noUnused* + bundler resolution, include=["src"]. vite.config.ts port 5173, outDir dist.
files: client/tsconfig.json (new), client/vite.config.ts (new), fix_plan.md, PROGRESS.md

## 2026-05-28 — task 9 README skeleton
verify: `grep -qi synk README.md`
result: TASK9_PASS. Title + section stubs (Quickstart, Architecture, hybrid brain, Upgrading, Docs, License) with TODO markers pointing at tasks 116-118.
files: README.md, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 10 protocol client->server messages
verify: `grep -q '"type": "join"' protocol/messages.md`
result: TASK10_PASS. Documented join/move/say/interact/leave with field shapes + JSON examples. Decided: position=[x,y,z] floats, facing=yaw radians, v=1.
files: protocol/messages.md, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 11 protocol server->client messages
verify: `grep -q '"type": "world_state"' protocol/messages.md`
result: TASK11_PASS. Documented welcome/world_state/agent_event/dialogue/error with field shapes + JSON examples. agent_event kinds: spoke/emoted/moved/gave_item/goal_changed/handoff.
files: protocol/messages.md, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 12 protocol pinned parameters
verify: `grep -qi throttle protocol/messages.md && grep -qi facing protocol/messages.md`
result: TASK12_PASS. Pinned: world_state throttle 10 Hz/100ms; nearby radius 12.0 xz units; facing = yaw radians (0=+x, CCW toward +z); structured-action→agent_event kind table.
files: protocol/messages.md, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 13 protocol versioning + examples
verify: `grep -c '"v":' protocol/messages.md`
result: TASK13_PASS, count=11 (every message example carries "v": 1). Added Versioning section: v required both directions, unknown v -> error "unsupported_version", additive-only within major.
files: protocol/messages.md, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 14 Vec3 dataclass + add/sub/mul
verify: `cd server && pytest tests/test_geometry.py -q` (via `python -m pytest`, venv active)
result: 5 passed. Vec3 frozen+slots dataclass, defaults 0; __add__/__sub__/__mul__/__rmul__.
files: server/synk/geometry.py, server/tests/test_geometry.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 15 Vec3 length/length_xz/normalize
verify: `cd server && pytest tests/test_geometry.py -q`
result: 9 passed. length (3D), length_xz (ignores y), normalize (zero->zero).
files: server/synk/geometry.py, server/tests/test_geometry.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 16 Vec3 distance_to (xz) + to/from list
verify: `cd server && pytest tests/test_geometry.py -q`
result: 11 passed. distance_to = xz distance; to_list/from_list roundtrip. Geometry phase (14-16) complete.
files: server/synk/geometry.py, server/tests/test_geometry.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 17 Entity base
verify: `cd server && pytest tests/test_world.py -q`
result: 3 passed. Entity dataclass (id, position=Vec3 default, zone="default"); mutable position.
files: server/synk/world.py, server/tests/test_world.py, fix_plan.md, PROGRESS.md
notes: WORKFLOW CHANGE — switching to commit directly on `main` (default branch) from here so each commit counts on the GitHub contribution graph. main fast-forwarded to include the harness + tasks 1-17. ralph/synk-v1 retained but loop now targets main.

## 2026-05-28 — task 18 Player + Agent skeletons
verify: `cd server && pytest tests/test_world.py -q`
result: 5 passed. Player(Entity){name, facing}; Agent(Entity){name, facing, personality, current_action="idle", goal=None}. Brain/memory attach later.
files: server/synk/world.py, server/tests/test_world.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 19 World add/remove
verify: `cd server && pytest tests/test_world.py -q`
result: 9 passed. World holds dict by id; add (ValueError on dup), remove (returns entity, KeyError if missing), __contains__, __len__.
files: server/synk/world.py, server/tests/test_world.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 20 World get-by-id + list-by-zone
verify: `cd server && pytest tests/test_world.py -q`
result: 11 passed. get (KeyError if missing), try_get (None), all(), by_zone(zone).
files: server/synk/world.py, server/tests/test_world.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 21 World within_radius (xz, zone-scoped)
verify: `cd server && pytest tests/test_world.py -q`
result: 13 passed. within_radius(center, radius, zone, exclude_id) — xz distance, boundary inclusive, never leaks across zones, optional self-exclude.
files: server/synk/world.py, server/tests/test_world.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 22 World tick counter + sim time
verify: `cd server && pytest tests/test_world.py -q`
result: 16 passed. tick:int + sim_time:float start at 0; advance(dt) increments tick and accrues sim_time; rejects negative dt. World & entities phase (17-22) complete.
files: server/synk/world.py, server/tests/test_world.py, fix_plan.md, PROGRESS.md

