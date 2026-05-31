// Local player: WASD movement and throttled move emission. Framing is handled
// separately by OrbitFollowCamera (see camera.ts), which reads this.mesh.position.

import * as THREE from "three";

export interface PlayerControllerOptions {
  speed?: number;
  emitIntervalMs?: number;
  onMove?: (position: [number, number, number], facing: number) => void;
}

export class PlayerController {
  readonly mesh: THREE.Mesh;
  private readonly keys = new Set<string>();
  private readonly speed: number;
  private readonly emitIntervalMs: number;
  private readonly onMove?: (position: [number, number, number], facing: number) => void;
  private lastEmit = 0;

  constructor(options: PlayerControllerOptions = {}) {
    this.speed = options.speed ?? 4;
    this.emitIntervalMs = options.emitIntervalMs ?? 100;
    this.onMove = options.onMove;
    this.mesh = new THREE.Mesh(
      new THREE.CapsuleGeometry(0.4, 1.0, 6, 12),
      new THREE.MeshStandardMaterial({ color: 0x4fa3ff }),
    );
    this.mesh.position.set(0, 1.0, 6);
    window.addEventListener("keydown", (e) => this.keys.add(e.key.toLowerCase()));
    window.addEventListener("keyup", (e) => this.keys.delete(e.key.toLowerCase()));
  }

  update(dt: number): void {
    let dx = 0;
    let dz = 0;
    if (this.keys.has("w") || this.keys.has("arrowup")) dz -= 1;
    if (this.keys.has("s") || this.keys.has("arrowdown")) dz += 1;
    if (this.keys.has("a") || this.keys.has("arrowleft")) dx -= 1;
    if (this.keys.has("d") || this.keys.has("arrowright")) dx += 1;

    if (dx !== 0 || dz !== 0) {
      const len = Math.hypot(dx, dz);
      dx /= len;
      dz /= len;
      this.mesh.position.x += dx * this.speed * dt;
      this.mesh.position.z += dz * this.speed * dt;
      this.mesh.rotation.y = -Math.atan2(dz, dx);
      this.maybeEmit(Math.atan2(dz, dx));
    }
  }

  private maybeEmit(facing: number): void {
    const now = performance.now();
    if (now - this.lastEmit < this.emitIntervalMs) return;
    this.lastEmit = now;
    const p = this.mesh.position;
    this.onMove?.([p.x, 0, p.z], facing);
  }
}
