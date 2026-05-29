"""Grid-based A* pathfinding on the xz-plane, around static circular obstacles."""

from __future__ import annotations

from dataclasses import dataclass

from .geometry import Vec3

Cell = tuple[int, int]  # (col, row) == (x-index, z-index)


@dataclass(frozen=True, slots=True)
class Obstacle:
    """A static circular obstacle on the xz-plane."""

    center: Vec3
    radius: float


class Grid:
    """A uniform occupancy grid over a rectangular region of the xz-plane."""

    def __init__(self, min_x: float, min_z: float, cols: int, rows: int, cell_size: float) -> None:
        if cols <= 0 or rows <= 0:
            raise ValueError("cols and rows must be positive")
        if cell_size <= 0:
            raise ValueError("cell_size must be positive")
        self.min_x = min_x
        self.min_z = min_z
        self.cols = cols
        self.rows = rows
        self.cell_size = cell_size
        self.blocked: set[Cell] = set()

    def in_bounds(self, cell: Cell) -> bool:
        col, row = cell
        return 0 <= col < self.cols and 0 <= row < self.rows

    def world_to_cell(self, pos: Vec3) -> Cell:
        col = int((pos.x - self.min_x) // self.cell_size)
        row = int((pos.z - self.min_z) // self.cell_size)
        return (col, row)

    def cell_center(self, cell: Cell) -> Vec3:
        col, row = cell
        x = self.min_x + (col + 0.5) * self.cell_size
        z = self.min_z + (row + 0.5) * self.cell_size
        return Vec3(x, 0.0, z)

    def is_blocked(self, cell: Cell) -> bool:
        return cell in self.blocked

    def block(self, cell: Cell) -> None:
        if self.in_bounds(cell):
            self.blocked.add(cell)

    @classmethod
    def from_obstacles(
        cls,
        min_x: float,
        min_z: float,
        cols: int,
        rows: int,
        cell_size: float,
        obstacles: list[Obstacle],
    ) -> Grid:
        grid = cls(min_x, min_z, cols, rows, cell_size)
        for col in range(cols):
            for row in range(rows):
                center = grid.cell_center((col, row))
                for obs in obstacles:
                    if center.distance_to(obs.center) <= obs.radius:
                        grid.block((col, row))
                        break
        return grid
