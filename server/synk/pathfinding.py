"""Grid-based A* pathfinding on the xz-plane, around static circular obstacles."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from .geometry import Vec3

Cell = tuple[int, int]  # (col, row) == (x-index, z-index)

_DIAGONAL = math.sqrt(2.0)


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

    def neighbors(self, cell: Cell) -> list[Cell]:
        """In-bounds, unblocked 8-connected neighbors. Diagonals that would clip
        the corner of a blocked cell are disallowed."""
        col, row = cell
        out: list[Cell] = []
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == 0 and dr == 0:
                    continue
                cand = (col + dc, row + dr)
                if not self.in_bounds(cand) or self.is_blocked(cand):
                    continue
                if dc != 0 and dr != 0:
                    if self.is_blocked((col + dc, row)) or self.is_blocked((col, row + dr)):
                        continue
                out.append(cand)
        return out


def _step_cost(a: Cell, b: Cell) -> float:
    return 1.0 if (a[0] == b[0] or a[1] == b[1]) else _DIAGONAL


def _octile(a: Cell, b: Cell) -> float:
    dx = abs(a[0] - b[0])
    dz = abs(a[1] - b[1])
    return (dx + dz) + (_DIAGONAL - 2.0) * min(dx, dz)


def _direction(a: Cell, b: Cell) -> Cell:
    def sign(n: int) -> int:
        return (n > 0) - (n < 0)

    return (sign(b[0] - a[0]), sign(b[1] - a[1]))


def simplify_path(path: list[Cell]) -> list[Cell]:
    """Drop interior cells that lie on a straight run, keeping only turn points
    (plus the start and goal). A grid path of unit steps becomes a short waypoint list."""
    if len(path) <= 2:
        return list(path)
    out: list[Cell] = [path[0]]
    for i in range(1, len(path) - 1):
        if _direction(path[i - 1], path[i]) != _direction(path[i], path[i + 1]):
            out.append(path[i])
    out.append(path[-1])
    return out


def astar(grid: Grid, start: Cell, goal: Cell) -> list[Cell]:
    """A* over the grid. Returns the cell path from start to goal inclusive, or
    [] if start/goal are invalid or no path exists."""
    if not (grid.in_bounds(start) and grid.in_bounds(goal)):
        return []
    if grid.is_blocked(start) or grid.is_blocked(goal):
        return []
    if start == goal:
        return [start]

    open_heap: list[tuple[float, Cell]] = [(0.0, start)]
    came_from: dict[Cell, Cell] = {}
    g_score: dict[Cell, float] = {start: 0.0}
    closed: set[Cell] = set()

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path
        if current in closed:
            continue
        closed.add(current)
        for nbr in grid.neighbors(current):
            tentative = g_score[current] + _step_cost(current, nbr)
            if nbr not in g_score or tentative < g_score[nbr]:
                g_score[nbr] = tentative
                came_from[nbr] = current
                heapq.heappush(open_heap, (tentative + _octile(nbr, goal), nbr))
    return []
