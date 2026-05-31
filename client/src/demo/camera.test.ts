import { describe, expect, it } from "vitest";

import { clamp, orbitOffset } from "./camera";

describe("orbitOffset (D4 orbit/follow camera)", () => {
  it("places the camera straight back at yaw=0, pitch=0", () => {
    const [x, y, z] = orbitOffset({ yaw: 0, pitch: 0, distance: 10 });
    expect(x).toBeCloseTo(0);
    expect(y).toBeCloseTo(0);
    expect(z).toBeCloseTo(10);
  });

  it("places the camera overhead at pitch=pi/2", () => {
    const [x, y, z] = orbitOffset({ yaw: 0, pitch: Math.PI / 2, distance: 10 });
    expect(x).toBeCloseTo(0);
    expect(y).toBeCloseTo(10);
    expect(z).toBeCloseTo(0);
  });

  it("orbits around the Y axis with yaw", () => {
    const [x, , z] = orbitOffset({ yaw: Math.PI / 2, pitch: 0, distance: 10 });
    expect(x).toBeCloseTo(10);
    expect(z).toBeCloseTo(0);
  });

  it("preserves distance regardless of orbit angle", () => {
    const [x, y, z] = orbitOffset({ yaw: 1.1, pitch: 0.5, distance: 12 });
    expect(Math.hypot(x, y, z)).toBeCloseTo(12);
  });
});

describe("clamp", () => {
  it("bounds values to [min, max]", () => {
    expect(clamp(-5, 0, 10)).toBe(0);
    expect(clamp(5, 0, 10)).toBe(5);
    expect(clamp(50, 0, 10)).toBe(10);
  });
});
