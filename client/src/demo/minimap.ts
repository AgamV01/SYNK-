// A small top-down minimap drawn to a 2D canvas: obstacles, NPCs, and the player.
// The world xz-plane is projected to canvas pixels; world +z maps downward on screen.

import type { AgentSnapshot } from "../sdk/types";
import type { Obstacle } from "./scene";

export interface MinimapProjectionOptions {
  size: number; // canvas size in px (square)
  worldExtent: number; // half-width of the world region shown, in world units
}

/** Project a world (x, z) onto minimap canvas pixels (origin top-left). Pure +
 *  unit-testable: world (0,0) is the center; +x is right, +z is down. */
export function worldToMinimap(
  x: number,
  z: number,
  opts: MinimapProjectionOptions,
): [number, number] {
  const half = opts.size / 2;
  const scale = half / opts.worldExtent;
  return [half + x * scale, half + z * scale];
}

export class Minimap {
  private readonly ctx: CanvasRenderingContext2D;
  private readonly size: number;
  private readonly worldExtent: number;

  constructor(
    root: HTMLElement,
    private readonly obstacles: Obstacle[] = [],
    options: Partial<MinimapProjectionOptions> = {},
  ) {
    this.size = options.size ?? 160;
    this.worldExtent = options.worldExtent ?? 30;
    const canvas = document.createElement("canvas");
    canvas.width = this.size;
    canvas.height = this.size;
    Object.assign(canvas.style, {
      position: "fixed",
      bottom: "16px",
      left: "16px",
      borderRadius: "10px",
      border: "1px solid #3a3a4a",
      background: "rgba(20,20,28,0.8)",
    } satisfies Partial<CSSStyleDeclaration>);
    root.appendChild(canvas);
    this.ctx = canvas.getContext("2d") as CanvasRenderingContext2D;
  }

  private dot(x: number, z: number, color: string, radius: number): void {
    const [px, py] = worldToMinimap(x, z, { size: this.size, worldExtent: this.worldExtent });
    this.ctx.fillStyle = color;
    this.ctx.beginPath();
    this.ctx.arc(px, py, radius, 0, Math.PI * 2);
    this.ctx.fill();
  }

  /** Redraw the minimap from the latest snapshot + the local player position. */
  render(agents: AgentSnapshot[], player: { x: number; z: number }): void {
    if (!this.ctx) return;
    this.ctx.clearRect(0, 0, this.size, this.size);
    for (const o of this.obstacles) this.dot(o.x, o.z, "#5a4632", Math.max(3, o.radius * 2));
    for (const a of agents) this.dot(a.position[0], a.position[2], "#ffb347", 3);
    this.dot(player.x, player.z, "#4fa3ff", 4);
  }
}
