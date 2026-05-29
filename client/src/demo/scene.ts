// The Three.js scene: ground, lighting, and static prop/obstacle meshes.

import * as THREE from "three";

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

  scene.add(new THREE.AmbientLight(0xffffff, 0.55));
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

  return { scene, camera, renderer, resize };
}
