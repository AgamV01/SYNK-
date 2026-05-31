import { describe, expect, it } from "vitest";

import { phaseLook } from "./scene";
import type { Phase } from "../sdk/types";

describe("phaseLook (D3 day/night cycle)", () => {
  it("returns a distinct look per phase", () => {
    const phases: Phase[] = ["morning", "day", "evening", "night"];
    const skies = phases.map((p) => phaseLook(p).sky);
    expect(new Set(skies).size).toBe(4); // all four sky colors differ
  });

  it("makes night dimmer than day", () => {
    expect(phaseLook("night").sunIntensity).toBeLessThan(phaseLook("day").sunIntensity);
    expect(phaseLook("night").ambient).toBeLessThan(phaseLook("day").ambient);
  });

  it("falls back to the day look for an unknown phase", () => {
    expect(phaseLook("noon" as Phase)).toEqual(phaseLook("day"));
  });
});
