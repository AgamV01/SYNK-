from __future__ import annotations

from synk.geometry import Vec3


def test_defaults_are_zero() -> None:
    assert Vec3() == Vec3(0.0, 0.0, 0.0)


def test_add() -> None:
    assert Vec3(1, 2, 3) + Vec3(4, 5, 6) == Vec3(5, 7, 9)


def test_sub() -> None:
    assert Vec3(4, 5, 6) - Vec3(1, 2, 3) == Vec3(3, 3, 3)


def test_mul_scalar_both_sides() -> None:
    assert Vec3(1, -2, 3) * 2 == Vec3(2, -4, 6)
    assert 2 * Vec3(1, -2, 3) == Vec3(2, -4, 6)


def test_is_frozen() -> None:
    import dataclasses

    v = Vec3(1, 2, 3)
    try:
        v.x = 9.0  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:  # pragma: no cover
        raise AssertionError("Vec3 should be immutable")
