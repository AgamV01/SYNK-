"""LLM providers. All are optional and guarded: the package imports and runs with
no provider installed and no API key, using MockProvider by default."""

from __future__ import annotations

import hashlib
from typing import Protocol, runtime_checkable


@runtime_checkable
class Provider(Protocol):
    """A text generator the deliberative brain calls off-tick.

    `generate` is async because real providers do network I/O. It must never be
    awaited on the simulation tick (see spec section 2)."""

    name: str

    async def generate(self, prompt: str, *, system: str | None = None) -> str: ...


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
