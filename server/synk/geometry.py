"""Minimal 3D vector math. The world is 3D but spatial queries use the xz-plane."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: Vec3) -> Vec3:
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vec3:
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    __rmul__ = __mul__

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def length_xz(self) -> float:
        return math.sqrt(self.x * self.x + self.z * self.z)

    def normalize(self) -> Vec3:
        """Unit vector in 3D. The zero vector normalizes to itself."""
        n = self.length()
        if n == 0.0:
            return Vec3(0.0, 0.0, 0.0)
        return Vec3(self.x / n, self.y / n, self.z / n)

    def distance_to(self, other: Vec3) -> float:
        """Ground-plane (xz) distance, ignoring height."""
        return (self - other).length_xz()

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z]

    @classmethod
    def from_list(cls, values: list[float] | tuple[float, float, float]) -> Vec3:
        x, y, z = values
        return cls(float(x), float(y), float(z))
