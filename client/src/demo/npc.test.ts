import { describe, expect, it } from "vitest";

import { clamp01, interpolate, interpolateAngle } from "./npc";

describe("interpolate (D1 snapshot interpolation)", () => {
  it("returns the endpoints at t=0 and t=1", () => {
    expect(interpolate(2, 10, 0)).toBe(2);
    expect(interpolate(2, 10, 1)).toBe(10);
  });

  it("returns the midpoint at t=0.5", () => {
    expect(interpolate(0, 10, 0.5)).toBe(5);
    expect(interpolate(-4, 4, 0.5)).toBe(0);
  });

  it("clamps t outside [0,1] so it never overshoots", () => {
    expect(interpolate(0, 10, -1)).toBe(0);
    expect(interpolate(0, 10, 2)).toBe(10);
  });
});

describe("clamp01", () => {
  it("clamps to the unit interval", () => {
    expect(clamp01(-0.5)).toBe(0);
    expect(clamp01(0.25)).toBe(0.25);
    expect(clamp01(3)).toBe(1);
  });
});

describe("interpolateAngle (shortest-path facing)", () => {
  it("interpolates linearly within a half turn", () => {
    expect(interpolateAngle(0, Math.PI / 2, 0.5)).toBeCloseTo(Math.PI / 4);
  });

  it("takes the short way across the ±pi wrap", () => {
    // From +3.0 rad to -3.0 rad is a short +0.283 rad step (through pi), not -6 rad.
    const result = interpolateAngle(3.0, -3.0, 0.5);
    const delta = -3.0 - 3.0 + 2 * Math.PI; // shortest signed delta ~ +0.283
    expect(result).toBeCloseTo(3.0 + delta * 0.5);
  });
});
