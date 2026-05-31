// Demo entry point: wire the SDK to the Three.js scene, NPCs, UI, and voice.

import { SynkClient } from "../sdk";
import type { AgentSnapshot } from "../sdk/types";
import { NPCManager } from "./npc";
import { PlayerController } from "./player";
import { createScene, type Obstacle } from "./scene";
import { DemoUI } from "./ui";
import { Voice } from "./voice";

const PLAYER_NAME = "Traveler";
const ZONE = "tavern";
const TALK_RADIUS = 3.0;
// Configurable for deploys (e.g. a Cloudflare Pages client + a Render/Fly server);
// defaults to a local backend on :8000.
const WS_URL = import.meta.env.VITE_SYNK_WS ?? `ws://${location.hostname || "localhost"}:8000/ws`;

const obstacles: Obstacle[] = [
  { x: -4, z: -2, radius: 1.2 },
  { x: 5, z: 1, radius: 1.0 },
];

const canvas = document.getElementById("scene") as HTMLCanvasElement;
const uiRoot = document.getElementById("ui") as HTMLElement;

const { scene, camera, renderer, resize } = createScene(canvas, obstacles);
window.addEventListener("resize", resize);

const npcs = new NPCManager(scene);
const voice = new Voice({ enabled: false }); // TTS/STT off by default
const client = new SynkClient();

const ui = new DemoUI(uiRoot, {
  onSay: (text) => {
    const target = ui.currentTarget;
    if (!target) return;
    client.say(target, text);
    ui.addDialogue("You", text, false);
  },
  onMic: () => {
    voice.enabled = true; // push-to-talk opt-in
    const started = voice.startListening((text) => {
      const target = ui.currentTarget;
      if (target && text.trim()) {
        ui.setChatText(text);
        client.say(target, text);
        ui.addDialogue("You", text, false);
      }
    });
    if (!started) {
      ui.addDialogue("system", "Speech recognition unavailable in this browser.", true);
    }
  },
});

const player = new PlayerController(camera, {
  onMove: (position, facing) => client.move(position, facing),
});
scene.add(player.mesh);

// Lightweight client-side mirror of agent state for the proximity + debug panels.
const agentNames = new Map<string, string>();
const agentActions = new Map<string, string>();
const recentActivity = new Map<string, string[]>();

function pushActivity(agentId: string, line: string): void {
  const log = recentActivity.get(agentId) ?? [];
  log.push(line);
  while (log.length > 5) log.shift();
  recentActivity.set(agentId, log);
}

function updateProximity(agents: AgentSnapshot[]): void {
  let nearest: AgentSnapshot | null = null;
  let best = TALK_RADIUS;
  const px = player.mesh.position.x;
  const pz = player.mesh.position.z;
  for (const a of agents) {
    const d = Math.hypot(a.position[0] - px, a.position[2] - pz);
    if (d <= best) {
      best = d;
      nearest = a;
    }
  }
  if (nearest) {
    ui.setNearbyAgent(nearest.id, nearest.name);
    ui.setAgentDebug({
      name: nearest.name,
      action: nearest.action,
      goal: null,
      recent: recentActivity.get(nearest.id),
    });
  } else {
    ui.setNearbyAgent(null, null);
    ui.setAgentDebug(null);
  }
}

client.onOpen(() => client.join(PLAYER_NAME, ZONE));

client.on("welcome", (msg) => {
  for (const a of msg.snapshot.agents) agentNames.set(a.id, a.name);
  npcs.update(msg.snapshot.agents);
});

client.on("world_state", (msg) => {
  for (const a of msg.agents) {
    agentNames.set(a.id, a.name);
    agentActions.set(a.id, a.action);
  }
  npcs.update(msg.agents);
  updateProximity(msg.agents);
});

client.on("dialogue", (msg) => {
  const name = agentNames.get(msg.agent_id) ?? msg.agent_id;
  ui.addDialogue(name, msg.text, msg.overheard ?? false);
  npcs.showSpeech(msg.agent_id, msg.text);
  voice.speak(msg.text);
  pushActivity(msg.agent_id, `said: ${msg.text}`);
});

client.on("agent_event", (msg) => {
  if (msg.kind === "emoted") {
    const emote = typeof msg.payload.emote === "string" ? msg.payload.emote : "emote";
    npcs.playEmote(msg.agent_id, emote);
    pushActivity(msg.agent_id, `emoted: ${emote}`);
  } else {
    pushActivity(msg.agent_id, msg.kind);
  }
});

client.on("error", (msg) => {
  ui.addDialogue("system", `${msg.code}: ${msg.message}`, true);
});

client.connect(WS_URL);

let last = performance.now();
function frame(now: number): void {
  const dt = Math.min((now - last) / 1000, 0.1);
  last = now;
  player.update(dt);
  npcs.animate();
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
