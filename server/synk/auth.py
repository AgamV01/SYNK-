"""Anonymous, short-lived session tokens. No passwords or accounts (v1): a token is
issued on join, scoped to a player id, and expires after a TTL."""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Session:
    token: str
    player_id: str
    expires_at: float


class AuthManager:
    def __init__(self, ttl: float = 3600.0, clock: Callable[[], float] | None = None) -> None:
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self.ttl = ttl
        self._clock = clock or time.monotonic
        self._sessions: dict[str, Session] = {}

    def issue(self, player_id: str) -> Session:
        """Mint a new opaque token bound to `player_id`, expiring after `ttl`."""
        token = secrets.token_urlsafe(24)
        session = Session(
            token=token,
            player_id=player_id,
            expires_at=self._clock() + self.ttl,
        )
        self._sessions[token] = session
        return session
