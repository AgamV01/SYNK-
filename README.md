# SYNK

Open-source framework for intelligent, LLM-driven NPCs in web-based 3D worlds. A server-authoritative Python runtime drives agent behavior, memory, and dialogue; a TypeScript SDK plus a Three.js demo render the world so a player can walk up, talk, and interact in real time.

The headline idea is the **hybrid brain**: a cheap reactive layer runs every tick with no network I/O, and the expensive LLM layer fires only on meaningful events. An idle world costs near zero; adding an API key upgrades NPC dialogue to real LLM reasoning.

> Status: under construction. See `fix_plan.md` for the build plan and `PROGRESS.md` for the journal.

## Quickstart

No API key required — the server runs the **MockProvider + reactive brain**, so NPCs
move, navigate, and talk out of the box. (Adding a key upgrades dialogue to a real LLM;
see [Upgrading](#upgrading-to-real-llm-dialogue).)

**Prerequisites:** Python 3.11+ and Node 18+.

**1. Backend** (serves the tavern world on `:8000`):

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn synk.server:app --port 8000
```

**2. Client** (Three.js demo, in a second terminal):

```bash
cd client
npm install
npm run dev
```

**3. Play:** open the URL Vite prints (default <http://localhost:5173>). Use **WASD**
to move, walk up to an NPC named Gus, Mira, or Tomas, and type in the chat box to talk.
The panel on the right shows the focused agent's live action and recent activity.

Sanity-check the runtime with no browser at all:

```bash
cd server && python examples/tavern.py --selftest   # 3 NPCs, 80 ticks
cd server && python examples/headless_demo.py --selftest
```

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
