from __future__ import annotations

import math

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


def test_length() -> None:
    assert Vec3(3, 4, 0).length() == 5.0
    assert math.isclose(Vec3(1, 2, 2).length(), 3.0)


def test_length_xz_ignores_y() -> None:
    assert Vec3(3, 100, 4).length_xz() == 5.0


def test_normalize_unit_length() -> None:
    n = Vec3(0, 0, 5).normalize()
    assert n == Vec3(0, 0, 1)
    assert math.isclose(Vec3(1, 1, 1).normalize().length(), 1.0)


def test_normalize_zero_is_zero() -> None:
    assert Vec3(0, 0, 0).normalize() == Vec3(0, 0, 0)


def test_distance_to_is_xz() -> None:
    assert Vec3(0, 0, 0).distance_to(Vec3(3, 999, 4)) == 5.0


def test_to_from_list_roundtrip() -> None:
    v = Vec3(1.5, -2.0, 3.25)
    assert v.to_list() == [1.5, -2.0, 3.25]
    assert Vec3.from_list(v.to_list()) == v
    assert Vec3.from_list((1, 2, 3)) == Vec3(1.0, 2.0, 3.0)


def test_is_frozen() -> None:
    import dataclasses

    v = Vec3(1, 2, 3)
    try:
        v.x = 9.0  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:  # pragma: no cover
        raise AssertionError("Vec3 should be immutable")
