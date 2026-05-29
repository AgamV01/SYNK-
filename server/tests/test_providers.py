from __future__ import annotations

from synk.brains.providers import Provider


class EchoProvider:
    name = "echo"

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        return prompt


def test_provider_protocol_is_satisfied() -> None:
    assert isinstance(EchoProvider(), Provider)


async def test_provider_generate_is_async() -> None:
    p = EchoProvider()
    assert await p.generate("hello") == "hello"
