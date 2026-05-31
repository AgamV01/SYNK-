from __future__ import annotations

from synk.brains.base import Wander
from synk.brains.llm import LLMBrain
from synk.geometry import Vec3
from synk.memory import MemoryItem, MemoryStore
from synk.perception import Percept
from synk.world import Agent


class ExplodingProvider:
    """Fails loudly if anyone calls it — used to prove decide() does no I/O."""

    name = "exploding"

    async def generate(self, prompt: str, *, system: str | None = None, **kwargs) -> str:
        raise AssertionError("provider must never be called from decide()")


class StubProvider:
    name = "stub"

    def __init__(self) -> None:
        self.last_prompt: str | None = None

    async def generate(self, prompt: str, *, system: str | None = None, **kwargs) -> str:
        self.last_prompt = prompt
        return "  A stubbed line of dialogue.  "


class FlakyProvider:
    """Fails `fail_times` then succeeds — exercises the retry path."""

    name = "flaky"

    def __init__(self, fail_times: int) -> None:
        self.fail_times = fail_times
        self.calls = 0

    async def generate(self, prompt: str, *, system: str | None = None, **kwargs) -> str:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("transient provider error")
        return "recovered dialogue"


class SlowProvider:
    """Sleeps longer than the timeout — exercises the timeout path."""

    name = "slow"

    async def generate(self, prompt: str, *, system: str | None = None, **kwargs) -> str:
        import asyncio

        await asyncio.sleep(10)
        return "too late"


def _percept(agent: Agent) -> Percept:
    return Percept(agent_id=agent.id, position=agent.position, tick=0)


def test_decide_delegates_to_reactive_without_io() -> None:
    brain = LLMBrain(provider=ExplodingProvider())
    agent = Agent(id="npc1", position=Vec3(0, 0, 0))
    # Alone + restless reactive default -> Wander, and the provider is never touched.
    assert isinstance(brain.decide(agent, _percept(agent)), Wander)


async def test_converse_uses_provider_when_present() -> None:
    provider = StubProvider()
    brain = LLMBrain(provider=provider)
    agent = Agent(id="npc1", name="Gus", personality="a gruff barkeep")
    result = await brain.converse(agent, _percept(agent), "what's on tap?")
    assert result.text == "A stubbed line of dialogue."  # provider output, trimmed
    assert provider.last_prompt is not None
    assert "what's on tap?" in provider.last_prompt


async def test_converse_degrades_to_reactive_without_provider() -> None:
    brain = LLMBrain(provider=None)  # zero-key path
    agent = Agent(id="npc1", name="Gus", personality="a gruff barkeep")
    result = await brain.converse(agent, _percept(agent), "hello there")
    # Falls back to the reactive templated greeting.
    assert "Gus" in result.text
    assert "hello there" in result.text


async def test_converse_includes_relationships_in_prompt() -> None:
    from synk.relationships import Relationships

    provider = StubProvider()
    brain = LLMBrain(provider=provider)
    agent = Agent(id="npc1", name="Gus")
    agent.relationships = Relationships()
    agent.relationships.adjust("player_1", 3.0)
    await brain.converse(agent, _percept(agent), "hi")
    assert provider.last_prompt is not None
    assert "How you feel about others" in provider.last_prompt
    assert "player_1" in provider.last_prompt


async def test_converse_assembles_memory_context_into_prompt() -> None:
    provider = StubProvider()
    brain = LLMBrain(provider=provider)
    agent = Agent(id="npc1", name="Gus", personality="a gruff barkeep")
    memory = MemoryStore()
    memory.add(MemoryItem(text="the player gave me a gold coin", ts=1.0, salience=5.0))
    agent.memory = memory  # duck-typed attachment
    await brain.converse(agent, _percept(agent), "remember me?")
    assert provider.last_prompt is not None
    assert "the player gave me a gold coin" in provider.last_prompt


async def test_converse_retries_flaky_provider_then_succeeds() -> None:
    # A2: a provider that fails twice then succeeds is retried up to success.
    provider = FlakyProvider(fail_times=2)
    brain = LLMBrain(provider=provider, retries=3)
    agent = Agent(id="npc1", name="Gus", personality="a gruff barkeep")
    result = await brain.converse(agent, _percept(agent), "hi")
    assert result.text == "recovered dialogue"
    assert provider.calls == 3  # 2 failures + 1 success


async def test_converse_falls_back_to_reactive_when_retries_exhausted() -> None:
    # A2: a provider that always fails exhausts retries and degrades to reactive.
    provider = FlakyProvider(fail_times=99)
    brain = LLMBrain(provider=provider, retries=2)
    agent = Agent(id="npc1", name="Gus", personality="a gruff barkeep")
    result = await brain.converse(agent, _percept(agent), "hello there")
    assert "Gus" in result.text  # reactive templated greeting
    assert "hello there" in result.text
    assert provider.calls == 3  # initial + 2 retries


async def test_converse_times_out_then_falls_back_to_reactive() -> None:
    # A2: a slow provider times out per attempt and degrades to reactive dialogue.
    provider = SlowProvider()
    brain = LLMBrain(provider=provider, timeout=0.05, retries=1)
    agent = Agent(id="npc1", name="Gus", personality="a gruff barkeep")
    result = await brain.converse(agent, _percept(agent), "hello there")
    assert "Gus" in result.text
    assert "hello there" in result.text
