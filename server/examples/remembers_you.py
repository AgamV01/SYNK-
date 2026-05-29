#!/usr/bin/env python
"""'Remembers you' demo: prove SYNK NPCs aren't stateless chatbots.

A player tells an NPC a fact, leaves, and returns — the NPC recalls it because the
agent's MemoryStore is folded into the LLM prompt (LLMBrain._assemble_context). Runs
offline: the provider here echoes whatever the prompt remembers, making recall visible.

    python examples/remembers_you.py --selftest
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from synk.brains.llm import LLMBrain
from synk.geometry import Vec3
from synk.memory import MemoryItem, MemoryStore, score_event_salience
from synk.perception import perceive
from synk.world import Agent, World


class RecallProvider:
    """Offline stand-in that surfaces the agent's remembered facts — so a real LLM's
    recall behavior is observable without a key."""

    name = "recall"

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        memories = [ln[2:] for ln in prompt.splitlines() if ln.startswith("- ")]
        if memories:
            return f"Of course — I remember that {memories[0]}."
        return "I don't believe we've met."


def build_world() -> tuple[World, Agent, LLMBrain]:
    world = World()
    agent = Agent(id="npc_archivist", name="Della", personality="a sharp-eyed archivist", zone="library")
    agent.memory = MemoryStore()
    world.add(agent)
    brain = LLMBrain(provider=RecallProvider())
    return world, agent, brain


async def run_selftest() -> None:
    world, agent, brain = build_world()

    # First visit: the NPC has never met the player.
    first = await brain.converse(agent, perceive(world, agent), "Hello there.")
    assert "haven't met" in first.text or "don't believe" in first.text, first.text

    # The player shares a fact; the server records it into the agent's memory.
    agent.memory.add(
        MemoryItem(text="the player Ada loves astronomy", ts=world.sim_time,
                   salience=score_event_salience("spoke"))
    )

    # ...player leaves and returns later (a fresh converse).
    world.advance(0.1)
    second = await brain.converse(agent, perceive(world, agent), "Do you remember me?")
    assert "astronomy" in second.text, f"NPC failed to recall: {second.text!r}"

    print("SELFTEST PASS: NPC forgot a stranger, then recalled the returning player ->")
    print(f"  {second.text}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SYNK 'remembers you' demo")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        asyncio.run(run_selftest())
    else:
        print("Run with --selftest to see an NPC recall a returning player.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
