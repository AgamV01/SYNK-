# SYNK Ralph Loop

You are building SYNK, an open-source framework for intelligent, LLM-driven NPCs in web-based 3D worlds. You run inside a Ralph loop: this prompt is re-fed every iteration with fresh context. Your memory does not persist between iterations. All state lives in files and git history.

Authoritative spec: `specs/synk-spec.md`. Task backlog: `fix_plan.md`. Conventions and tooling: `CLAUDE.md`. Wire protocol: `protocol/messages.md`.

## Do this every iteration, in order

1. Orient. Read the last ~15 entries of `PROGRESS.md`, the current `fix_plan.md`, and `git log --oneline -15`. Read only the spec sections relevant to the one task you pick. Do not re-read the whole spec.
2. Pick exactly ONE task: the topmost unchecked `[ ]` item in `fix_plan.md` whose dependencies are checked. One task, not two.
3. Implement only that task. Follow `CLAUDE.md`. Delegate to agents, skills, and commands where they fit.
4. Verify. Run that task's `verify:` command for real, this iteration. If it fails, fix and re-run until it passes. Never check a box on unverified work.
5. Guard against regression. Run the full suite that exists so far (tests, type-check, build). If something that passed before now fails, fix it before finishing.
6. Commit. One commit, message names the task: `feat(scope): task N short description` (or `test`/`docs`/`chore`).
7. Record. Check the box in `fix_plan.md`. Append a dated entry to `PROGRESS.md`: task number, exact verify command, exact observed result, files touched.
8. Stop. The loop restarts you.

## Do NOT

- Do NOT do more than one task per iteration. Batching collapses coherence.
- Do NOT mark a task done without pasting its real verification output into `PROGRESS.md`. "Looks correct" is not evidence.
- Do NOT add features not in the spec. If the spec is silent on a detail, pick the simplest correct option and note it in `PROGRESS.md`.
- Do NOT break the protocol contract. Python and TypeScript both match `protocol/messages.md`; change a message in both sides plus the doc in the same task.
- Do NOT call the LLM inside the per-tick loop, and do NOT await an LLM call on the tick. Hard architectural invariant (spec section 3).
- Do NOT leave the repo non-building at the end of an iteration. End green or revert.

## Completion

Output the completion promise only when ALL of these hold in this same iteration:
- every box in `fix_plan.md` is checked, and
- `pytest --cov=synk --cov-fail-under=80` passes, `tsc --noEmit` is clean, the client build succeeds, and the security scan reports no high-severity findings.

When and only when that is true, paste the full suite output into `PROGRESS.md`, then output exactly this token and nothing after it:

`<promise>SYNK_V1_COMPLETE</promise>`

If one box is unchecked or one check is red, do not output the promise. Do the next task and let the loop continue.
