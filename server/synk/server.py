"""FastAPI WebSocket server implementing the SYNK protocol (protocol/messages.md).

Clients send intents (join/move/say/interact/leave); the server is authoritative and
streams welcome/world_state/agent_event/dialogue/error back."""

from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="SYNK")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
