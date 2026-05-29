# synk

Server-authoritative Python runtime for **SYNK** — an open-source framework for intelligent,
LLM-driven NPCs in web-based 3D worlds.

The **hybrid brain**: a cheap reactive layer runs every tick with zero network I/O; the LLM
layer fires only on meaningful events, off the tick. NPCs perceive, pathfind (A\*), remember
(salience + decay + reflection), converse, and act — and an idle world costs essentially zero.

```bash
pip install synk          # core (zero API keys needed; MockProvider + reactive brain)
pip install "synk[llm]"   # add Anthropic + OpenAI providers
uvicorn synk.server:app --port 8000
```

Full docs, the TypeScript SDK, and the Three.js demo: <https://github.com/AgamV01/SYNK->
