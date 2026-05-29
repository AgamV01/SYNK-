from __future__ import annotations

from synk.brains.providers import MockProvider, Provider


class EchoProvider:
    name = "echo"

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        return prompt


def test_provider_protocol_is_satisfied() -> None:
    assert isinstance(EchoProvider(), Provider)


async def test_provider_generate_is_async() -> None:
    p = EchoProvider()
    assert await p.generate("hello") == "hello"


def test_mock_provider_satisfies_protocol() -> None:
    assert isinstance(MockProvider(), Provider)
    assert MockProvider().name == "mock"


async def test_mock_provider_is_context_flavored() -> None:
    p = MockProvider()
    out = await p.generate("Tell me about the ancient treasure")
    assert "treasure" in out  # longest salient word leaks into the reply


async def test_mock_provider_is_deterministic() -> None:
    p = MockProvider()
    a = await p.generate("same prompt here")
    b = await p.generate("same prompt here")
    assert a == b


async def test_mock_provider_handles_empty_prompt() -> None:
    p = MockProvider()
    out = await p.generate("")
    assert "this" in out
