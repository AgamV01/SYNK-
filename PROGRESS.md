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

