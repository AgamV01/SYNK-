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

