// NPC avatars driven by world_state snapshots: capsule bodies with name labels.

import * as THREE from "three";

import type { AgentSnapshot } from "../sdk/types";

// world_state arrives ~every 100 ms (protocol/messages.md). We interpolate between the
// last two snapshots over this window so motion is smooth instead of teleporting.
export const SNAPSHOT_MS = 100;

/** Clamp `t` to [0,1]. */
export function clamp01(t: number): number {
  return t < 0 ? 0 : t > 1 ? 1 : t;
}

/** Linear interpolation from `prev` to `next` at fraction `t` (clamped to [0,1]). */
export function interpolate(prev: number, next: number, t: number): number {
  return prev + (next - prev) * clamp01(t);
}

/** Interpolate an angle (radians) along the shortest path, so facing never spins
 *  the long way around when crossing the ±π wrap. */
export function interpolateAngle(prev: number, next: number, t: number): number {
  let delta = next - prev;
  while (delta > Math.PI) delta -= 2 * Math.PI;
  while (delta < -Math.PI) delta += 2 * Math.PI;
  return prev + delta * clamp01(t);
}

interface NPCView {
  group: THREE.Group;
  body: THREE.Mesh;
  bubble: THREE.Sprite | null;
  bubbleExpiry: number;
  emoteUntil: number;
  // Interpolation endpoints (xz + yaw) and the time the latest snapshot landed.
  fromX: number;
  fromZ: number;
  fromYaw: number;
  toX: number;
  toZ: number;
  toYaw: number;
  lerpStart: number;
}

function makeLabel(text: string): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 64;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.fillStyle = "rgba(10,10,18,0.7)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.font = "28px system-ui, sans-serif";
    ctx.fillStyle = "#fff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, canvas.width / 2, canvas.height / 2);
  }
  const texture = new THREE.CanvasTexture(canvas);
  const sprite = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: texture, transparent: true }),
  );
  sprite.scale.set(2.2, 0.55, 1);
  sprite.position.set(0, 1.7, 0);
  return sprite;
}

function makeBubble(text: string): THREE.Sprite {
  const clipped = text.length > 48 ? `${text.slice(0, 47)}…` : text;
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 96;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.fillStyle = "rgba(255,255,255,0.92)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.font = "26px system-ui, sans-serif";
    ctx.fillStyle = "#14141c";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(clipped, canvas.width / 2, canvas.height / 2);
  }
  const sprite = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true }),
  );
  sprite.scale.set(4, 0.75, 1);
  sprite.position.set(0, 2.4, 0);
  return sprite;
}

export class NPCManager {
  private readonly views = new Map<string, NPCView>();

  constructor(private readonly scene: THREE.Scene) {}

  update(agents: AgentSnapshot[]): void {
    const seen = new Set<string>();
    const now = performance.now();
    for (const agent of agents) {
      seen.add(agent.id);
      const view = this.views.get(agent.id) ?? this.create(agent);
      // Re-anchor the interpolation: start from where we're currently rendered and
      // ease toward the new snapshot over the next snapshot window.
      view.fromX = view.group.position.x;
      view.fromZ = view.group.position.z;
      view.fromYaw = view.group.rotation.y;
      view.toX = agent.position[0];
      view.toZ = agent.position[2];
      view.toYaw = -agent.facing;
      view.lerpStart = now;
    }
    for (const [id, view] of this.views) {
      if (!seen.has(id)) {
        this.scene.remove(view.group);
        this.views.delete(id);
      }
    }
  }

  private create(agent: AgentSnapshot): NPCView {
    const group = new THREE.Group();
    const body = new THREE.Mesh(
      new THREE.CapsuleGeometry(0.4, 1.0, 6, 12),
      new THREE.MeshStandardMaterial({ color: 0xffb347 }),
    );
    group.add(body);
    group.add(makeLabel(agent.name || agent.id));
    group.position.set(agent.position[0], 1.0, agent.position[2]);
    group.rotation.y = -agent.facing;
    this.scene.add(group);
    const view: NPCView = {
      group,
      body,
      bubble: null,
      bubbleExpiry: 0,
      emoteUntil: 0,
      fromX: agent.position[0],
      fromZ: agent.position[2],
      fromYaw: -agent.facing,
      toX: agent.position[0],
      toZ: agent.position[2],
      toYaw: -agent.facing,
      lerpStart: performance.now(),
    };
    this.views.set(agent.id, view);
    return view;
  }

  /** Show a speech bubble above an agent for `durationMs`. */
  showSpeech(agentId: string, text: string, durationMs = 4000): void {
    const view = this.views.get(agentId);
    if (!view) return;
    if (view.bubble) view.group.remove(view.bubble);
    const bubble = makeBubble(text);
    view.group.add(bubble);
    view.bubble = bubble;
    view.bubbleExpiry = performance.now() + durationMs;
  }

  /** Trigger a brief emote bounce on an agent. */
  playEmote(agentId: string, _emote: string, durationMs = 600): void {
    const view = this.views.get(agentId);
    if (!view) return;
    view.emoteUntil = performance.now() + durationMs;
  }

  /** Advance per-frame animations: interpolate positions/facing toward the latest
   *  snapshot, expire bubbles, animate emote bounces. */
  animate(): void {
    const now = performance.now();
    for (const view of this.views.values()) {
      const t = (now - view.lerpStart) / SNAPSHOT_MS;
      view.group.position.x = interpolate(view.fromX, view.toX, t);
      view.group.position.z = interpolate(view.fromZ, view.toZ, t);
      view.group.rotation.y = interpolateAngle(view.fromYaw, view.toYaw, t);
      if (view.bubble && now > view.bubbleExpiry) {
        view.group.remove(view.bubble);
        view.bubble = null;
      }
      if (now < view.emoteUntil) {
        view.body.position.y = Math.abs(Math.sin(now * 0.02)) * 0.3;
      } else if (view.body.position.y !== 0) {
        view.body.position.y = 0;
      }
    }
  }
}
