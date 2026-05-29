from __future__ import annotations

import pytest

from synk.auth import AuthManager


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def test_rejects_bad_ttl() -> None:
    with pytest.raises(ValueError):
        AuthManager(ttl=0)


def test_issue_returns_scoped_token() -> None:
    clock = FakeClock()
    auth = AuthManager(ttl=100.0, clock=clock)
    session = auth.issue("player_1")
    assert session.player_id == "player_1"
    assert session.token
    assert session.expires_at == 100.0


def test_issued_tokens_are_unique() -> None:
    auth = AuthManager()
    a = auth.issue("p1")
    b = auth.issue("p1")
    assert a.token != b.token


def test_validate_live_token() -> None:
    clock = FakeClock()
    auth = AuthManager(ttl=100.0, clock=clock)
    session = auth.issue("p1")
    clock.t = 50.0
    assert auth.validate(session.token) is session


def test_validate_expired_token_returns_none() -> None:
    clock = FakeClock()
    auth = AuthManager(ttl=100.0, clock=clock)
    session = auth.issue("p1")
    clock.t = 100.0  # exactly at expiry -> expired
    assert auth.validate(session.token) is None
    # Evicted, so a later check is still None.
    clock.t = 50.0
    assert auth.validate(session.token) is None


def test_validate_unknown_token() -> None:
    auth = AuthManager()
    assert auth.validate("not-a-real-token") is None


def test_token_is_scoped_to_player() -> None:
    auth = AuthManager()
    session = auth.issue("player_1")
    assert auth.is_for(session.token, "player_1") is True
    assert auth.is_for(session.token, "player_2") is False


def test_is_for_expired_token_is_false() -> None:
    clock = FakeClock()
    auth = AuthManager(ttl=10.0, clock=clock)
    session = auth.issue("player_1")
    clock.t = 10.0
    assert auth.is_for(session.token, "player_1") is False
