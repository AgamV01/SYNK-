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


# Isometric projection (2:1 dimetric) for a 3D-ish look.
ISO = 15.0  # pixels per world unit
COS, SIN = 0.866, 0.5
ORIGIN_X, ORIGIN_Y = SIZE / 2, 150.0
GROUND_HALF = 8.0  # world extent of the ground plane


def to_px(x: float, z: float, y: float = 0.0) -> tuple[float, float]:
    sx = ORIGIN_X + (x - z) * ISO * COS
    sy = ORIGIN_Y + (x + z) * ISO * SIN - y * ISO
    return (sx, sy)


def render_frame(world, tavern, bubble: str | None) -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)

    # Ground as an isometric diamond.
    g = GROUND_HALF
    draw.polygon(
        [to_px(-g, -g), to_px(g, -g), to_px(g, g), to_px(-g, g)], fill=GROUND
    )
    # Iso grid lines.
    for i in range(-8, 9, 2):
        draw.line([to_px(i, -g), to_px(i, g)], fill=(54, 54, 70))
        draw.line([to_px(-g, i), to_px(g, i)], fill=(54, 54, 70))

    for obs in tavern.obstacles:
        cx, cy = to_px(obs.center.x, obs.center.z)
        r = obs.radius * ISO
        draw.ellipse([cx - r, cy - r * SIN, cx + r, cy + r * SIN], fill=(60, 50, 38))
        draw.rectangle([cx - r, cy - r * SIN - 22, cx + r, cy + r * SIN], fill=OBSTACLE)
        draw.ellipse([cx - r, cy - r * SIN - 22 - r * SIN, cx + r, cy - 22 + r * SIN], fill=(112, 88, 64))

    def figure(pos: Vec3, color, label: str | None = None) -> None:
        sx, sy = to_px(pos.x, pos.z)
        draw.ellipse([sx - 8, sy - 4, sx + 8, sy + 4], fill=(0, 0, 0))  # shadow
        draw.ellipse([sx - 6, sy - 26, sx + 6, sy - 6], fill=color)  # body
        draw.ellipse([sx - 5, sy - 36, sx + 5, sy - 26], fill=color)  # head
        if label:
            draw.text((sx - len(label) * 3, sy - 52), label, fill=TEXT)

    # Draw back-to-front for correct overlap.
    figures: list[tuple[float, object]] = []
    for agent_id in tavern.brains:
        a = world.get(agent_id)
        figures.append((a.position.x + a.position.z, (a, NPC, a.name)))
    player = world.try_get("player_1")
    if player is not None:
        figures.append((player.position.x + player.position.z, (player, PLAYER, "You")))
    for _, (ent, color, label) in sorted(figures, key=lambda f: f[0]):
        figure(ent.position, color, label)

    if bubble is not None:
        gus = world.get("npc_gus")
        bx, by = to_px(gus.position.x, gus.position.z)
        text = bubble if len(bubble) <= 46 else bubble[:43] + "..."
        w = 8 + 6 * len(text)
        draw.rounded_rectangle([bx - w / 2, by - 78, bx + w / 2, by - 52], radius=6, fill=BUBBLE_BG)
        draw.text((bx - w / 2 + 6, by - 72), text, fill=BUBBLE_TEXT)

    draw.text((22, SIZE - 30), "SYNK - tavern (engine-rendered, isometric)", fill=(150, 150, 170))
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
