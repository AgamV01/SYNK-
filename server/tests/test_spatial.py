from __future__ import annotations

import random

import pytest

from synk.geometry import Vec3
from synk.spatial import SpatialIndex
from synk.world import Entity, World


def test_rejects_bad_cell_size() -> None:
    with pytest.raises(ValueError):
        SpatialIndex([], 0)


def test_matches_brute_force_within_radius() -> None:
    rng = random.Random(1234)
    for _ in range(40):
        world = World()
        for i in range(60):
            world.add(
                Entity(
                    id=f"e{i}",
                    position=Vec3(rng.uniform(-30, 30), 0, rng.uniform(-30, 30)),
                    zone=rng.choice(["a", "b"]),
                )
            )
        index = SpatialIndex(world.all(), cell_size=10.0)
        center = Vec3(rng.uniform(-30, 30), 0, rng.uniform(-30, 30))
        radius = rng.uniform(1.0, 20.0)
        zone = rng.choice(["a", "b"])
        got = {e.id for e in index.within_radius(center, radius, zone, exclude_id="e0")}
        want = {e.id for e in world.within_radius(center, radius, zone, exclude_id="e0")}
        assert got == want
