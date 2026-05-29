from __future__ import annotations

import pytest

from synk.geometry import Vec3
from synk.pathfinding import Grid, Obstacle


def test_grid_rejects_bad_dims() -> None:
    with pytest.raises(ValueError):
        Grid(0, 0, 0, 5, 1.0)
    with pytest.raises(ValueError):
        Grid(0, 0, 5, 5, 0.0)


def test_world_to_cell_and_center() -> None:
    g = Grid(min_x=0.0, min_z=0.0, cols=10, rows=10, cell_size=1.0)
    assert g.world_to_cell(Vec3(0.5, 0, 0.5)) == (0, 0)
    assert g.world_to_cell(Vec3(3.2, 0, 7.9)) == (3, 7)
    assert g.cell_center((0, 0)) == Vec3(0.5, 0.0, 0.5)


def test_in_bounds() -> None:
    g = Grid(0, 0, 4, 4, 1.0)
    assert g.in_bounds((0, 0))
    assert g.in_bounds((3, 3))
    assert not g.in_bounds((4, 0))
    assert not g.in_bounds((-1, 2))


def test_from_obstacles_blocks_covered_cells() -> None:
    obstacles = [Obstacle(center=Vec3(5.0, 0, 5.0), radius=1.0)]
    g = Grid.from_obstacles(0, 0, 10, 10, 1.0, obstacles)
    # Cell (5,5) center is (5.5,_,5.5), distance to (5,5) ~0.707 < 1.0 -> blocked.
    assert g.is_blocked((5, 5))
    # A far corner cell is open.
    assert not g.is_blocked((0, 0))


def test_from_obstacles_empty_list() -> None:
    g = Grid.from_obstacles(0, 0, 5, 5, 1.0, [])
    assert g.blocked == set()
