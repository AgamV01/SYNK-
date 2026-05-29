// NPC avatars driven by world_state snapshots: capsule bodies with name labels.

import * as THREE from "three";

import type { AgentSnapshot } from "../sdk/types";

interface NPCView {
  group: THREE.Group;
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

export class NPCManager {
  private readonly views = new Map<string, NPCView>();

  constructor(private readonly scene: THREE.Scene) {}

  update(agents: AgentSnapshot[]): void {
    const seen = new Set<string>();
    for (const agent of agents) {
      seen.add(agent.id);
      const view = this.views.get(agent.id) ?? this.create(agent);
      view.group.position.set(agent.position[0], 1.0, agent.position[2]);
      view.group.rotation.y = -agent.facing;
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
    this.scene.add(group);
    const view: NPCView = { group };
    this.views.set(agent.id, view);
    return view;
  }
}
