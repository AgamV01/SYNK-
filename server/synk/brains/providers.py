"""LLM providers. All are optional and guarded: the package imports and runs with
no provider installed and no API key, using MockProvider by default."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Provider(Protocol):
    """A text generator the deliberative brain calls off-tick.

    `generate` is async because real providers do network I/O. It must never be
    awaited on the simulation tick (see spec section 2)."""

    name: str

    async def generate(self, prompt: str, *, system: str | None = None) -> str: ...
