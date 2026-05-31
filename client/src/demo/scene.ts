// The Three.js scene: ground, lighting, and static prop/obstacle meshes.

import * as THREE from "three";

import type { Phase } from "../sdk/types";

export interface Obstacle {
  x: number;
  z: number;
  radius: number;
}

export interface SceneBundle {
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  renderer: THREE.WebGLRenderer;
  resize: () => void;
  applyPhase: (phase: Phase) => void;
}

export interface PhaseLook {
  sky: number; // background + fog color
  sun: number; // directional light color
  sunIntensity: number;
  ambient: number; // ambient light intensity
  sunPos: [number, number, number];
}

// Lighting palette per time-of-day phase. Pure data, so it can be unit-tested and the
// day/night cycle is driven entirely by the world_state `phase` field (see B5).
const PHASE_LOOKS: Record<Phase, PhaseLook> = {
  morning: { sky: 0x9fb6c8, sun: 0xffe0b0, sunIntensity: 0.85, ambient: 0.6, sunPos: [10, 7, 6] },
  day: { sky: 0x8fb7e0, sun: 0xffffff, sunIntensity: 1.05, ambient: 0.7, sunPos: [4, 14, 4] },
  evening: { sky: 0x4a3b50, sun: 0xff9a52, sunIntensity: 0.8, ambient: 0.45, sunPos: [-10, 5, -4] },
  night: { sky: 0x10131f, sun: 0x6a78b0, sunIntensity: 0.4, ambient: 0.3, sunPos: [-4, 9, -8] },
};

export function phaseLook(phase: Phase): PhaseLook {
  return PHASE_LOOKS[phase] ?? PHASE_LOOKS.day;
}

export function createScene(
  canvas: HTMLCanvasElement,
  obstacles: Obstacle[] = [],
): SceneBundle {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x14141c);
  scene.fog = new THREE.Fog(0x14141c, 25, 60);

  const camera = new THREE.PerspectiveCamera(
    60,
    window.innerWidth / window.innerHeight,
    0.1,
    1000,
  );
  camera.position.set(0, 9, 11);
  camera.lookAt(0, 0, 0);

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(60, 60),
    new THREE.MeshStandardMaterial({ color: 0x2a2a38 }),
  );
  ground.rotation.x = -Math.PI / 2;
  scene.add(ground);

  const grid = new THREE.GridHelper(60, 30, 0x3a3a4a, 0x262632);
  scene.add(grid);

  const ambient = new THREE.AmbientLight(0xffffff, 0.55);
  scene.add(ambient);
  const sun = new THREE.DirectionalLight(0xffffff, 0.9);
  sun.position.set(6, 12, 8);
  scene.add(sun);

  for (const obstacle of obstacles) {
    const prop = new THREE.Mesh(
      new THREE.CylinderGeometry(obstacle.radius, obstacle.radius, 1.6, 20),
      new THREE.MeshStandardMaterial({ color: 0x5a4632 }),
    );
    prop.position.set(obstacle.x, 0.8, obstacle.z);
    scene.add(prop);
  }

  const resize = (): void => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  };

  // Apply a time-of-day look: sky/fog color, sun color/intensity/direction, ambient.
  const applyPhase = (phase: Phase): void => {
    const look = phaseLook(phase);
    (scene.background as THREE.Color).setHex(look.sky);
    if (scene.fog) (scene.fog as THREE.Fog).color.setHex(look.sky);
    sun.color.setHex(look.sun);
    sun.intensity = look.sunIntensity;
    sun.position.set(...look.sunPos);
    ambient.intensity = look.ambient;
  };

  return { scene, camera, renderer, resize, applyPhase };
}
