# SYNK

Open-source framework for intelligent, LLM-driven NPCs in web-based 3D worlds. A server-authoritative Python runtime drives agent behavior, memory, and dialogue; a TypeScript SDK plus a Three.js demo render the world so a player can walk up, talk, and interact in real time.

The headline idea is the **hybrid brain**: a cheap reactive layer runs every tick with no network I/O, and the expensive LLM layer fires only on meaningful events. An idle world costs near zero; adding an API key upgrades NPC dialogue to real LLM reasoning.

> Status: under construction. See `fix_plan.md` for the build plan and `PROGRESS.md` for the journal.

## Quickstart

_TODO (task 116): zero-config quickstart with exact run steps._

## Architecture

_TODO (task 117): mermaid diagram of World / Agent / Brain / Simulation / Server layers._

## The hybrid brain

_TODO (task 117): reactive-every-tick vs. LLM-on-events, and why it keeps idle worlds cheap._

## Upgrading to real LLM dialogue

_TODO (task 117): set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` to swap MockProvider for a real provider._

## Documentation

- _TODO (task 118): writing a custom brain._
- _TODO (task 118): adding a custom structured action._

## License

MIT — see [LICENSE](LICENSE).
