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

## 2026-05-28 — task 23 Percept + WorldEvent dataclasses
verify: `cd server && pytest tests/test_perception.py -q`
result: 2 passed. WorldEvent{kind,source_id,zone,tick,position,salience,payload} in world.py. Percept{agent_id,position,tick,nearby:[Entity],events:[WorldEvent]} in perception.py.
files: server/synk/world.py, server/synk/perception.py, server/tests/test_perception.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 24 perceive() within sense radius
verify: `cd server && pytest tests/test_perception.py -q`
result: 3 passed. perceive(world, agent, sense_radius=10) builds Percept via within_radius (self excluded). DEFAULT_SENSE_RADIUS=10.
files: server/synk/perception.py, server/tests/test_perception.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 25 perception zone-scoping
verify: `cd server && pytest tests/test_perception.py -q`
result: 4 passed. Added test: entity at identical position but different zone is NOT perceived (enforced by within_radius zone filter). No impl change needed.
files: server/tests/test_perception.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 26 recent perceivable events feed
verify: `cd server && pytest tests/test_perception.py -q` (+ test_world.py regression, 22 passed total)
result: 6 perception passed. World.emit_event / recent_events(within_ticks). perceive() now includes events filtered by zone + sense radius + recency (DEFAULT_EVENT_RECENCY_TICKS=2), excluding self-sourced. Perception phase (23-26) complete.
files: server/synk/world.py, server/synk/perception.py, server/tests/test_perception.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 27 pathfinding Grid from obstacles
verify: `cd server && pytest tests/test_pathfinding.py -q`
result: 5 passed. Grid(min_x,min_z,cols,rows,cell_size) with world_to_cell/cell_center/in_bounds/is_blocked/block. Obstacle(center,radius). from_obstacles blocks cells whose center is within an obstacle radius.
files: server/synk/pathfinding.py, server/tests/test_pathfinding.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 28 A* core
verify: `cd server && pytest tests/test_pathfinding.py -q`
result: 8 passed. 8-connected A* with octile heuristic, heapq open set, closed set, no diagonal corner-cutting. Returns cell path incl endpoints, or [] for invalid/blocked endpoints. Grid.neighbors() added.
files: server/synk/pathfinding.py, server/tests/test_pathfinding.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 29 straight path on empty grid
verify: `cd server && pytest tests/test_pathfinding.py -q`
result: 10 passed. Confirmed A* yields the optimal straight diagonal [(0,0)..(4,4)] and orthogonal paths of Chebyshev+1 length on empty grids. Test-only (impl already correct).
files: server/tests/test_pathfinding.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 30 path around obstacle
verify: `cd server && pytest tests/test_pathfinding.py -q`
result: 11 passed. Wall at col 3 (rows 0-5, gap at row 6); A* detours through the gap, never steps on blocked cells, path strictly longer than the 7-cell straight crossing. Proves non-naive navigation.
files: server/tests/test_pathfinding.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 31 waypoint simplification
verify: `cd server && pytest tests/test_pathfinding.py -q`
result: 15 passed. simplify_path() keeps only turn points (+endpoints) via per-step direction sign; collapses straight runs, preserves endpoints on detours, short paths unchanged.
files: server/synk/pathfinding.py, server/tests/test_pathfinding.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 32 no-path returns empty
verify: `cd server && pytest tests/test_pathfinding.py -q`
result: 16 passed. Goal walled off on all 8 neighbors -> astar returns []. Pathfinding phase (27-32) complete.
files: server/tests/test_pathfinding.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 33 MemoryItem dataclass
verify: `cd server && pytest tests/test_memory.py -q`
result: 2 passed. MemoryItem{text, ts (sim seconds), salience=1.0}.
files: server/synk/memory.py, server/tests/test_memory.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 34 MemoryStore add + capacity cap
verify: `cd server && pytest tests/test_memory.py -q`
result: 5 passed. MemoryStore(capacity) rejects <=0; add() appends and, when over capacity, evicts least-salient (tie -> oldest ts). items property returns a copy.
files: server/synk/memory.py, server/tests/test_memory.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 35 salience scoring helper
verify: `cd server && pytest tests/test_memory.py -q`
result: 7 passed. SALIENCE_BY_KIND table + score_event_salience(kind) with DEFAULT_SALIENCE=1.0 fallback (gave_item>spoke>moved).
files: server/synk/memory.py, server/tests/test_memory.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 36 memory decay
verify: `cd server && pytest tests/test_memory.py -q`
result: 10 passed. MemoryStore.decay(dt, rate=0.05, floor=0.05) multiplies salience by exp(-rate*dt) then forgets items below floor; rejects negative dt.
notes: decay is multiplicative PER CALL (not based on item.ts age) so periodic calls compose correctly; exp(-rate*dt) with large dt*rate annihilates everything — keep test params modest.
files: server/synk/memory.py, server/tests/test_memory.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 37 recall recent N
verify: `cd server && pytest tests/test_memory.py -q`
result: 12 passed. recall_recent(n) returns n newest by ts (desc); n<=0 -> [].
files: server/synk/memory.py, server/tests/test_memory.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 38 recall top-salient K
verify: `cd server && pytest tests/test_memory.py -q`
result: 14 passed. recall_salient(k) returns k highest-salience (ties: newer ts first); k<=0 -> [].
files: server/synk/memory.py, server/tests/test_memory.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 39 recall union + dedupe + ordering
verify: `cd server && pytest tests/test_memory.py -q`
result: 16 passed. recall(recent_n=5, salient_k=5) = recent ∪ salient, deduped by id, newest-first. Memory phase (33-39) complete.
files: server/synk/memory.py, server/tests/test_memory.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 40 core action types
verify: `cd server && pytest tests/test_brain_contract.py -q`
result: 3 passed. brains/base.py: frozen Idle/Wander/MoveTo(target)/Face(target_id)/Emote(emote) with ClassVar kind labels; Action union alias.
files: server/synk/brains/base.py, server/tests/test_brain_contract.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 41 deliberative action types
verify: `cd server && pytest tests/test_brain_contract.py -q`
result: 5 passed. Added GiveItem(item,to_id)/SetGoal(goal)/Handoff(to_id,topic); extended Action union.
files: server/synk/brains/base.py, server/tests/test_brain_contract.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 42 Brain Protocol + dummy brain
verify: `cd server && pytest tests/test_brain_contract.py -q`
result: 8 passed (incl. 1 async). Brain runtime_checkable Protocol: sync decide(agent,percept)->Action, async converse(agent,percept,utterance)->ConverseResult{text, action?}. TYPE_CHECKING imports avoid import cycle with world/perception.
notes: CONFIRMED pytest-asyncio works with pytest 9.0.3 under asyncio_mode=auto (async def test ran). Earlier compatibility worry cleared.
files: server/synk/brains/base.py, server/tests/test_brain_contract.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 43 goal representation
verify: `cd server && pytest tests/test_brain_contract.py -q`
result: 10 passed. Goal{description, priority=1.0, created_ts=0.0, done=False}.complete(). Brain interface phase (40-43) complete. (Agent.goal stays a simple str label; Goal is the richer structured form for brains.)
files: server/synk/brains/base.py, server/tests/test_brain_contract.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 44 reactive idle/wander selection
verify: `cd server && pytest tests/test_reactive.py -q`
result: 2 passed. ReactiveBrain(sense_radius, arrive_radius, restless, grid). decide() ambient: Wander if restless else Idle. Minimal templated converse() (enriched at task 48). Helper _percept in test.
files: server/synk/brains/reactive.py, server/tests/test_reactive.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 45 approach nearby player
verify: `cd server && pytest tests/test_reactive.py -q`
result: 4 passed. _nearest_player() finds closest Player in percept; decide() returns MoveTo(player.position) when one is present, else ambient.
files: server/synk/brains/reactive.py, server/tests/test_reactive.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 46 steering toward target via path
verify: `cd server && pytest tests/test_reactive.py -q`
result: 5 passed. _steer_towards() uses astar+simplify_path on the brain's grid, returns MoveTo(cell_center of path[1]); straight MoveTo when grid is None. decide() now routes approach through it. Wall test confirms waypoint is unblocked and not straight at the walled-off player.
files: server/synk/brains/reactive.py, server/tests/test_reactive.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 47 face entity at arrive radius
verify: `cd server && pytest tests/test_reactive.py -q`
result: 7 passed. decide(): within arrive_radius of nearest player -> Face(player.id); beyond -> MoveTo (steer).
files: server/synk/brains/reactive.py, server/tests/test_reactive.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 48 templated greeting converse
verify: `cd server && pytest tests/test_reactive.py -q`
result: 9 passed. converse() templated greeting using name + personality + echo of utterance; default question on empty input. No LLM (zero-key path).
files: server/synk/brains/reactive.py, server/tests/test_reactive.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 49 utility scoring
verify: `cd server && pytest tests/test_reactive.py -q`
result: 11 passed. decide() now = max utility over _candidates(): Face 3.0 > approach 2.0 > Wander 1.0(restless) > Idle 0.1; calm flips wander/idle to 0.2/0.5. Behavior unchanged, selection now principled.
files: server/synk/brains/reactive.py, server/tests/test_reactive.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 50 emote on event
verify: `cd server && pytest tests/test_reactive.py -q`
result: 13 passed. _candidates() adds Emote(react_<kind>) at utility 1.5 when percept has events (reacts to most salient); beats ambient, loses to social (approach 2.0 / face 3.0). Reactive brain phase (44-50) complete.
files: server/synk/brains/reactive.py, server/tests/test_reactive.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 51 headless demo
verify: `cd server && python examples/headless_demo.py --selftest`
result: "SELFTEST PASS: agent approached and faced the player". DT=0.1 (10Hz), AGENT_SPEED=2.0. apply_action() = minimal demo stepper (MoveTo steers+faces, Face turns, Emote/Wander/Idle set label). step()=perceive->decide->apply->advance. --selftest asserts 100 ticks, distance decreased, reached arrive_radius, ends action=face. --ticks N prints log.
notes: apply_action here is a demo stand-in; canonical per-tick apply comes in Simulation phase (86-91).
files: server/examples/headless_demo.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 52 headless obstacle navigation
verify: `cd server && python examples/headless_demo.py --selftest`
result: both selftests PASS. Added build_obstacle_scene (wall col3 rows0-5, gap row6) + _selftest_obstacle: agent reaches player around the wall within 400 ticks, never enters a blocked cell, max_z>5 proves detour toward the gap.
files: server/examples/headless_demo.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 53 headless scripted greeting
verify: `cd server && python examples/headless_demo.py --selftest`
result: all 3 selftests PASS (greeting -> 'Gus: Well met. You said, "hello, barkeep".'). _selftest_greeting uses asyncio.run on brain.converse. Headless sanity phase (51-53) complete.
files: server/examples/headless_demo.py, fix_plan.md, PROGRESS.md

## 2026-05-28 — task 54 provider interface
verify: `cd server && pytest tests/test_providers.py -q`
result: 2 passed. Provider runtime_checkable Protocol: name + async generate(prompt, *, system=None)->str. EchoProvider test impl.
files: server/synk/brains/providers.py, server/tests/test_providers.py, fix_plan.md, PROGRESS.md

