#!/usr/bin/env python
"""Render docs/demo.gif from the REAL SYNK engine — no browser needed.

Runs the actual tavern world + Simulation + reactive brains, scripts the player
walking up to Gus and saying hello, and draws each tick top-down with Pillow into an
animated GIF. This is an engine-rendered view (not the 3D Three.js capture), useful as
a lightweight README demo. Requires Pillow:  pip install pillow

    python tools/render_demo_gif.py
"""

from __future__ import annotations

import asyncio
import math
import sys
from pathlib import Path

# Make the package importable when run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

from PIL import Image, ImageDraw  # noqa: E402

from synk.geometry import Vec3  # noqa: E402
from synk.simulation import Simulation  # noqa: E402
from synk.world import Player  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server" / "examples"))
from tavern import build_tavern  # noqa: E402

SIZE = 480
WORLD_MIN, WORLD_MAX = -9.0, 9.0
SCALE = SIZE / (WORLD_MAX - WORLD_MIN)
FRAMES = 64
FRAME_MS = 90

BG = (20, 20, 28)
GROUND = (42, 42, 56)
OBSTACLE = (90, 70, 50)
NPC = (255, 179, 71)
PLAYER = (79, 163, 255)
TEXT = (235, 235, 235)
BUBBLE_BG = (240, 240, 245)
BUBBLE_TEXT = (20, 20, 28)


def to_px(x: float, z: float) -> tuple[float, float]:
    return ((x - WORLD_MIN) * SCALE, (z - WORLD_MIN) * SCALE)


def render_frame(world, tavern, bubble: str | None) -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, SIZE - 20, SIZE - 20], fill=GROUND)

    # Faint grid.
    for i in range(-8, 9, 2):
        gx, _ = to_px(i, 0)
        _, gz = to_px(0, i)
        draw.line([(gx, 20), (gx, SIZE - 20)], fill=(50, 50, 64))
        draw.line([(20, gz), (SIZE - 20, gz)], fill=(50, 50, 64))

    for obs in tavern.obstacles:
        cx, cz = to_px(obs.center.x, obs.center.z)
        r = obs.radius * SCALE
        draw.ellipse([cx - r, cz - r, cx + r, cz + r], fill=OBSTACLE)

    def dot(pos: Vec3, color, label: str | None = None, radius: int = 9) -> None:
        px, pz = to_px(pos.x, pos.z)
        draw.ellipse([px - radius, pz - radius, px + radius, pz + radius], fill=color)
        if label:
            draw.text((px - radius, pz - radius - 14), label, fill=TEXT)

    for agent_id in tavern.brains:
        agent = world.get(agent_id)
        dot(agent.position, NPC, agent.name)

    player = world.try_get("player_1")
    if player is not None:
        dot(player.position, PLAYER, "You")

    if bubble is not None:
        gus = world.get("npc_gus")
        bx, bz = to_px(gus.position.x, gus.position.z)
        text = bubble if len(bubble) <= 46 else bubble[:43] + "..."
        w = 8 + 6 * len(text)
        draw.rounded_rectangle(
            [bx - w / 2, bz - 56, bx + w / 2, bz - 30], radius=6, fill=BUBBLE_BG
        )
        draw.text((bx - w / 2 + 6, bz - 50), text, fill=BUBBLE_TEXT)

    draw.text((26, SIZE - 34), "SYNK - tavern (engine-rendered)", fill=(150, 150, 170))
    return img


def main() -> int:
    tavern = build_tavern()
    world = tavern.world
    sim = Simulation(world, dt=0.1)
    for agent_id, brain in tavern.brains.items():
        sim.register(agent_id, brain)

    player = Player(id="player_1", name="You", position=Vec3(0, 0, 6.5), zone="tavern")
    world.add(player)
    gus_brain = tavern.brains["npc_gus"]

    frames: list[Image.Image] = []
    bubble: str | None = None
    for _ in range(FRAMES):
        gus = world.get("npc_gus")
        # Script the player walking toward Gus.
        delta = gus.position - player.position
        dist = delta.length_xz()
        if dist > 1.4:
            direction = Vec3(delta.x, 0, delta.z).normalize()
            player.position = player.position + direction * 0.28
        elif bubble is None:
            # Close enough: say hello and capture Gus's reactive reply.
            from synk.perception import perceive

            result = asyncio.run(
                gus_brain.converse(gus, perceive(world, gus), "hello there")
            )
            bubble = result.text
        sim.step()
        frames.append(render_frame(world, tavern, bubble))

    out = Path(__file__).resolve().parent.parent / "docs" / "demo.gif"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_MS,
        loop=0,
        optimize=False,
        disposal=2,
    )
    print(f"wrote {out} ({len(frames)} frames, {out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
