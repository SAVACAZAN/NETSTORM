"""
Render a NetStorm .fort map as a PNG image.

Uses the 16x16 tile grid + the actual tile sprites from _shapes.shp.

Important: tile_id mapping to sprite groups is NOT yet known.
This renderer uses heuristic assumptions:
  - tile_id 0x63 (= 99) = water (most common in MyOnlineGame)
  - other tile_ids = land/special, color-coded for now

Output: extracted/maps/<map_name>.png with isometric projection
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image, ImageDraw, ImageFont
from src.netstorm.assets.tarc import load as load_tarc
from src.netstorm.assets.fort import FortFile


GAME_DIR = Path(r"C:\Kits work\limaje de programare\9_GAMES\NetStorm-Islands-at-War_Win_EN_RIP-Version\NetStorm RIP")
OUT_DIR = Path(__file__).parent / "extracted" / "maps"

# Tile size for ISO rendering (placeholder — real game uses 32x16)
TILE_W = 64
TILE_H = 32


def tile_color(tile_id: int) -> tuple[int, int, int, int]:
    """Heuristic color for tile_id."""
    if tile_id == 0x63:  # water
        return (40, 80, 160, 255)
    if tile_id == 0x00:
        return (160, 140, 100, 255)  # sand?
    # Hash-based deterministic color for unknown tiles
    h = tile_id * 2654435761 & 0xFFFFFFFF
    return ((h >> 16) & 0xFF, (h >> 8) & 0xFF, h & 0xFF, 255)


def render_iso(fort: "FortFile", name: str, out_path: Path) -> None:
    """Render the map in isometric projection using colored diamonds."""
    width = 16
    height = 16

    # ISO size: each tile becomes a diamond TILE_W wide, TILE_H tall
    canvas_w = (width + height) * TILE_W // 2 + TILE_W
    canvas_h = (width + height) * TILE_H // 2 + TILE_H * 4

    img = Image.new("RGBA", (canvas_w, canvas_h), (20, 20, 30, 255))
    draw = ImageDraw.Draw(img, "RGBA")

    # Compute tile distribution from list[FortTile]
    tile_dist: Counter[int] = Counter()
    for tile in fort.tiles:
        tile_dist[tile.type_id] += 1

    # Draw tiles back-to-front
    for y in range(height):
        for x in range(width):
            idx = y * width + x
            tile = fort.tiles[idx]
            tile_id = tile.type_id

            # ISO transform: (x, y) → screen
            screen_x = (x - y) * TILE_W // 2 + canvas_w // 2 - TILE_W // 2
            screen_y = (x + y) * TILE_H // 2 + TILE_H

            color = tile_color(tile_id)

            # Draw diamond
            cx = screen_x + TILE_W // 2
            cy = screen_y + TILE_H // 2
            diamond = [
                (cx, screen_y),                  # top
                (screen_x + TILE_W, cy),         # right
                (cx, screen_y + TILE_H),         # bottom
                (screen_x, cy),                  # left
            ]
            draw.polygon(diamond, fill=color, outline=(0, 0, 0, 100))

    # Title overlay
    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
    draw.text((10, 10), name, fill=(255, 200, 0, 255), font=font)
    draw.text((10, 35), f"{width}x{height} grid", fill=(200, 200, 200, 255), font=font)
    y_off = 55
    for tid, cnt in tile_dist.most_common(10):
        c = tile_color(tid)
        draw.rectangle([10, y_off, 30, y_off + 18], fill=c, outline=(0, 0, 0, 255))
        draw.text((35, y_off), f"id 0x{tid:02X} = {cnt} tiles", fill=(220, 220, 220, 255), font=font)
        y_off += 22

    img.save(out_path)
    print(f"  Rendered: {out_path.name} ({canvas_w}x{canvas_h})")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    archive = load_tarc(GAME_DIR / "netstorm.tarc")

    # Render MyOnlineGame.fort (the only one on disk)
    print("Rendering MyOnlineGame.fort (from disk)...")
    fort_data = (GAME_DIR / "d" / "MyOnlineGame.fort").read_bytes()
    fort = FortFile(fort_data)
    render_iso(fort, "MyOnlineGame", OUT_DIR / "MyOnlineGame.png")

    # Render all .fort from TARC
    print("\nRendering all .fort files from TARC...")
    fort_names = [e.name for e in archive.entries
                  if e.name.lower().endswith(".fort")]

    for fort_path in fort_names:
        try:
            data = archive.get(fort_path)
            if not data:
                continue
            fort = FortFile(data)
            short = fort_path.replace("\\d\\", "").replace("/d/", "").replace(".fort", "")
            render_iso(fort, short, OUT_DIR / f"{short}.png")
        except Exception as e:
            print(f"  ERR rendering {fort_path}: {e}")


if __name__ == "__main__":
    main()
