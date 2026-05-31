import { describe, expect, it } from "vitest";

import { worldToMinimap } from "./minimap";

const OPTS = { size: 160, worldExtent: 30 };

describe("worldToMinimap (D6 minimap projection)", () => {
  it("maps the world origin to the canvas center", () => {
    expect(worldToMinimap(0, 0, OPTS)).toEqual([80, 80]);
  });

  it("maps +x to the right and +z downward", () => {
    const [px, py] = worldToMinimap(30, 30, OPTS);
    expect(px).toBe(160); // +worldExtent -> right edge
    expect(py).toBe(160); // +worldExtent -> bottom edge
  });

  it("maps negatives toward the top-left", () => {
    const [px, py] = worldToMinimap(-30, -30, OPTS);
    expect(px).toBe(0);
    expect(py).toBe(0);
  });
});
