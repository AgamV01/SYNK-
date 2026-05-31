// Orbit/follow camera: follows a target (the player) while the mouse can drag to orbit
// and the wheel can zoom. WASD movement stays in PlayerController; this only frames it.

import * as THREE from "three";

export interface Spherical {
  yaw: number; // radians around the Y axis
  pitch: number; // radians above the horizon
  distance: number; // units from the target
}

/** Camera offset from a target for a given orbit (pure, unit-testable). Returns the
 *  [x, y, z] vector to add to the target position. */
export function orbitOffset(s: Spherical): [number, number, number] {
  const cosPitch = Math.cos(s.pitch);
  return [
    s.distance * cosPitch * Math.sin(s.yaw),
    s.distance * Math.sin(s.pitch),
    s.distance * cosPitch * Math.cos(s.yaw),
  ];
}

/** Clamp a value to [min, max]. */
export function clamp(value: number, min: number, max: number): number {
  return value < min ? min : value > max ? max : value;
}

export interface OrbitCameraOptions {
  yaw?: number;
  pitch?: number;
  distance?: number;
  minPitch?: number;
  maxPitch?: number;
  minDistance?: number;
  maxDistance?: number;
  sensitivity?: number; // radians per pixel dragged
}

export class OrbitFollowCamera {
  yaw: number;
  pitch: number;
  distance: number;
  private readonly minPitch: number;
  private readonly maxPitch: number;
  private readonly minDistance: number;
  private readonly maxDistance: number;
  private readonly sensitivity: number;
  private dragging = false;
  private lastX = 0;
  private lastY = 0;

  constructor(
    private readonly camera: THREE.PerspectiveCamera,
    dom: HTMLElement,
    options: OrbitCameraOptions = {},
  ) {
    this.yaw = options.yaw ?? 0;
    this.pitch = options.pitch ?? 0.67;
    this.distance = options.distance ?? 12.8;
    this.minPitch = options.minPitch ?? 0.15;
    this.maxPitch = options.maxPitch ?? 1.45;
    this.minDistance = options.minDistance ?? 4;
    this.maxDistance = options.maxDistance ?? 30;
    this.sensitivity = options.sensitivity ?? 0.006;

    dom.addEventListener("mousedown", (e) => {
      this.dragging = true;
      this.lastX = e.clientX;
      this.lastY = e.clientY;
    });
    window.addEventListener("mouseup", () => {
      this.dragging = false;
    });
    window.addEventListener("mousemove", (e) => {
      if (!this.dragging) return;
      this.yaw -= (e.clientX - this.lastX) * this.sensitivity;
      this.pitch = clamp(
        this.pitch - (e.clientY - this.lastY) * this.sensitivity,
        this.minPitch,
        this.maxPitch,
      );
      this.lastX = e.clientX;
      this.lastY = e.clientY;
    });
    dom.addEventListener(
      "wheel",
      (e) => {
        this.distance = clamp(
          this.distance + e.deltaY * 0.01,
          this.minDistance,
          this.maxDistance,
        );
      },
      { passive: true },
    );
  }

  /** Position the camera to orbit-follow `target` this frame. */
  update(target: THREE.Vector3): void {
    const [ox, oy, oz] = orbitOffset({ yaw: this.yaw, pitch: this.pitch, distance: this.distance });
    this.camera.position.set(target.x + ox, target.y + oy, target.z + oz);
    this.camera.lookAt(target);
  }
}
