"""LLM providers. All are optional and guarded: the package imports and runs with
no provider installed and no API key, using MockProvider by default."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable, Mapping
from typing import Protocol, runtime_checkable


@runtime_checkable
class Provider(Protocol):
    """A text generator the deliberative brain calls off-tick.

    `generate` is async because real providers do network I/O. It must never be
    awaited on the simulation tick (see spec section 2)."""

    name: str

    async def generate(self, prompt: str, *, system: str | None = None) -> str: ...


def build_prompt(
    personality: str,
    memories: list[str],
    history: list[tuple[str, str]],
    utterance: str,
) -> str:
    """Assemble an NPC dialogue prompt from personality, recalled memories, and
    conversation history. Provider-agnostic plain text so any backend can use it."""
    persona = personality or "a nondescript character"
    lines = [
        f"You are {persona}. Stay in character. Reply in one or two sentences.",
    ]
    if memories:
        lines.append("\nWhat you remember:")
        lines.extend(f"- {m}" for m in memories)
    if history:
        lines.append("\nConversation so far:")
        lines.extend(f"{speaker}: {text}" for speaker, text in history)
    lines.append(f'\nThe player says: "{utterance}"')
    lines.append("Your reply:")
    return "\n".join(lines)


_MOCK_TEMPLATES = (
    'Hmm, "{kw}"... let me consider that.',
    'Ah, you mention "{kw}". Interesting.',
    '"{kw}", is it? I have thoughts on that.',
    'About "{kw}" — there is more than meets the eye.',
)


class MockProvider:
    """Zero-config default provider. Deterministic and offline: it produces a
    context-flavored line derived from the prompt, so the demo has "talking" NPCs
    with no API key."""

    name = "mock"

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        keyword = self._keyword(prompt)
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        idx = int(digest, 16) % len(_MOCK_TEMPLATES)
        return _MOCK_TEMPLATES[idx].format(kw=keyword)

    @staticmethod
    def _keyword(prompt: str) -> str:
        words = [w.strip(".,!?\"'()") for w in prompt.split()]
        words = [w for w in words if w.isalpha() and len(w) > 3]
        if not words:
            return "this"
        # Longest word as a cheap proxy for the most salient term.
        return max(words, key=len)


class AnthropicProvider:
    """Claude-backed provider. Guarded: importing this module never requires the
    `anthropic` SDK, and constructing the provider never needs a key. The SDK is
    imported lazily in `generate`, which raises a clear error if it or the key is
    missing — so the package always imports and runs (falling back to Mock)."""

    name = "anthropic"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 256,
    ) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.max_tokens = max_tokens

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - exercised only without the SDK
            raise RuntimeError(
                "AnthropicProvider requires the 'anthropic' package; install synk[llm]."
            ) from exc
        if not self.api_key:
            raise RuntimeError("AnthropicProvider requires ANTHROPIC_API_KEY to be set.")
        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        kwargs: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        message = await client.messages.create(**kwargs)
        return "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        )


class OpenAIProvider:
    """OpenAI-backed provider. Guarded exactly like AnthropicProvider: lazy SDK
    import, constructs without a key, clear error from `generate` if unavailable."""

    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        max_tokens: int = 256,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.max_tokens = max_tokens

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        try:
            import openai
        except ImportError as exc:  # pragma: no cover - exercised only without the SDK
            raise RuntimeError(
                "OpenAIProvider requires the 'openai' package; install synk[llm]."
            ) from exc
        if not self.api_key:
            raise RuntimeError("OpenAIProvider requires OPENAI_API_KEY to be set.")
        client = openai.AsyncOpenAI(api_key=self.api_key)
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = await client.chat.completions.create(
            model=self.model, max_tokens=self.max_tokens, messages=messages
        )
        return response.choices[0].message.content or ""


# Registry of provider factories by name. Mock is always present; the guarded LLM
# providers are registered too and only touch their SDKs lazily in `generate`.
_PROVIDERS: dict[str, Callable[[], Provider]] = {
    "mock": MockProvider,
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
}


def select_provider(env: Mapping[str, str] | None = None) -> Provider:
    """Choose a provider from the environment.

    Explicit `SYNK_PROVIDER` wins. Otherwise auto-detect from API keys. With no
    keys and no override, fall back to MockProvider, so the package runs with zero
    configuration. An unknown or unavailable choice also falls back to Mock."""
    env = os.environ if env is None else env
    choice = env.get("SYNK_PROVIDER", "").strip().lower()
    if not choice:
        if env.get("ANTHROPIC_API_KEY"):
            choice = "anthropic"
        elif env.get("OPENAI_API_KEY"):
            choice = "openai"
        else:
            choice = "mock"
    factory = _PROVIDERS.get(choice, MockProvider)
    return factory()
