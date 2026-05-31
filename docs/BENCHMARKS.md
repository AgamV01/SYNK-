# Benchmarks

Reproduce locally — no API key required:

```bash
python tools/benchmark.py
```

## The claim, quantified

SYNK's thesis is the **hybrid brain**: the reactive layer runs every tick with zero I/O, and
the LLM fires *only on meaningful events*. Two measurements back that up.

### 1. An idle world spends ~zero

> Idle cost: **100 NPCs × 200 ticks, no events → 0 LLM calls**

NPCs wander, perceive, and pathfind every tick using only the reactive layer. With nothing
salient happening, the deliberative (LLM) layer never fires — so an idle world of NPCs costs
**nothing** in tokens, no matter how many there are. LLM cost tracks *events*, not headcount.

### 2. Per-tick cost stays within the real-time budget

Per-tick reactive cost (perception via the spatial index + decide/apply for every agent).
Sample run on an Apple-silicon laptop, Python 3.12, agents packed on a 3-unit grid (a dense
stress case — neighborhoods are full):

| agents | ticks/sec | ms/tick |
|-------:|----------:|--------:|
|     10 |    11,444 |   0.087 |
|     50 |       686 |   1.458 |
|    100 |       219 |   4.567 |
|    250 |        55 |  18.340 |
|    500 |        23 |  42.582 |

The simulation targets **10 Hz** — a 100 ms per-tick budget. Every row above is under it: even
**500 NPCs tick in ~43 ms**, leaving headroom at the default rate. The uniform spatial hash
(`synk/spatial.py`, built once per tick) keeps perception tractable instead of O(agents²); a
realistically sparse world scales better than this packed worst case.

Numbers are machine-dependent — run the script for your hardware. They measure pure reactive
tick cost; LLM latency is off the tick by design and never blocks it.
