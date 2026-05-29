from __future__ import annotations

import pytest

from synk.brains.providers import (
    AnthropicProvider,
    MockProvider,
    OpenAIProvider,
    Provider,
    build_prompt,
    select_provider,
)


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


def test_select_defaults_to_mock_with_no_keys() -> None:
    assert isinstance(select_provider({}), MockProvider)


def test_select_explicit_mock() -> None:
    assert isinstance(select_provider({"SYNK_PROVIDER": "mock"}), MockProvider)


def test_select_unknown_choice_falls_back_to_mock() -> None:
    assert isinstance(select_provider({"SYNK_PROVIDER": "nonsense"}), MockProvider)


def test_anthropic_constructs_without_key_or_sdk() -> None:
    # Must not crash even with no key and the SDK absent.
    p = AnthropicProvider(api_key=None)
    assert p.name == "anthropic"
    assert isinstance(p, Provider)


def test_anthropic_is_selectable() -> None:
    assert isinstance(select_provider({"SYNK_PROVIDER": "anthropic"}), AnthropicProvider)


async def test_anthropic_generate_raises_clearly_without_sdk_or_key() -> None:
    # In this env the 'anthropic' SDK is not installed -> clear RuntimeError, no crash on import.
    with pytest.raises(RuntimeError):
        await AnthropicProvider(api_key=None).generate("hello")


def test_openai_constructs_without_key_or_sdk() -> None:
    p = OpenAIProvider(api_key=None)
    assert p.name == "openai"
    assert isinstance(p, Provider)


def test_openai_is_selectable() -> None:
    assert isinstance(select_provider({"SYNK_PROVIDER": "openai"}), OpenAIProvider)


async def test_openai_generate_raises_clearly_without_sdk_or_key() -> None:
    with pytest.raises(RuntimeError):
        await OpenAIProvider(api_key=None).generate("hello")


def test_build_prompt_includes_all_context() -> None:
    prompt = build_prompt(
        personality="a gruff barkeep named Gus",
        memories=["the player gave me a coin", "a brawl broke out last night"],
        history=[("Ada", "good evening"), ("Gus", "evening")],
        utterance="what's on tap?",
    )
    assert "gruff barkeep named Gus" in prompt
    assert "the player gave me a coin" in prompt
    assert "a brawl broke out last night" in prompt
    assert "Ada: good evening" in prompt
    assert "what's on tap?" in prompt


def test_build_prompt_handles_empty_context() -> None:
    prompt = build_prompt(personality="", memories=[], history=[], utterance="hi")
    assert "nondescript character" in prompt
    assert "hi" in prompt
