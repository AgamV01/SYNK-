"""A uniform spatial hash over the xz-plane for fast neighborhood queries.

Built once per tick from the current entities; querying touches only the buckets that
overlap the search radius, turning per-agent perception from O(n) into ~O(1). Results
match World.within_radius exactly (zone-scoped, xz distance, boundary-inclusive)."""

from __future__ import annotations

import math
from collections.abc import Iterable

from .geometry import Vec3
from .world import Entity

Cell = tuple[str, int, int]  # (zone, col, row)


class SpatialIndex:
    def __init__(self, entities: Iterable[Entity], cell_size: float = 10.0) -> None:
        if cell_size <= 0:
            raise ValueError("cell_size must be positive")
        self.cell_size = cell_size
        self._buckets: dict[Cell, list[Entity]] = {}
        for entity in entities:
            self._buckets.setdefault(self._cell(entity.zone, entity.position), []).append(entity)

    def _cell(self, zone: str, pos: Vec3) -> Cell:
        return (zone, math.floor(pos.x / self.cell_size), math.floor(pos.z / self.cell_size))

    def within_radius(
        self,
        center: Vec3,
        radius: float,
        zone: str,
        exclude_id: str | None = None,
    ) -> list[Entity]:
        span = int(radius // self.cell_size) + 1
        c0 = math.floor(center.x / self.cell_size)
        r0 = math.floor(center.z / self.cell_size)
        out: list[Entity] = []
        for dc in range(-span, span + 1):
            for dr in range(-span, span + 1):
                for entity in self._buckets.get((zone, c0 + dc, r0 + dr), ()):
                    if entity.id == exclude_id:
                        continue
                    if center.distance_to(entity.position) <= radius:
                        out.append(entity)
        return out
