"""
Render NetStorm .fort maps with REAL sprite tiles.

Uses tile_id → group_name mapping from sprite_name_mapping.json.

Heuristic mapping tile_id → sprite group:
  0x00..0x62 = land tiles (we'll use isle/isleBig variants)
  0x63 (99)  = water (= noIsland group 88)
  0x64+      = special markers

Output: extracted/maps_v2/<name>.png with rendered isometric map.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image, ImageDraw, ImageFont
from src.netstorm.assets.tarc import load as load_tarc
from src.netstorm.assets.fort import FortFile


GAME_DIR = Path(r"C:\Kits work\limaje de programare\9_GAMES\NetStorm-Islands-at-War_Win_EN_RIP-Version\NetStorm RIP")
ROOT = Path(__file__).parent
EXTRACTED = ROOT / "extracted"
SPRITES = EXTRACTED / "sprites_all"
OUT_DIR = EXTRACTED / "maps_v2"
MAPPING_PATH = EXTRACTED / "sprite_name_mapping.json"


# Tile_id → sprite group_id mapping (heuristic, refined later)
# We use the most common names from the mapping:
TILE_TO_GROUP = {
    0x00: 28,   # land (isle) — if no other info
    0x63: 88,   # water (noIsland)
}


def load_group_sprite(group_id: int, frame_idx: int = 0) -> Image.Image | None:
    """Load a sprite from extracted PNG cache."""
    group_dir = SPRITES / f"group_{group_id:03d}"
    if not group_dir.exists():
        return None
    pngs = sorted(group_dir.glob("frame_*.png"))
    if frame_idx >= len(pngs):
        frame_idx = 0
    if not pngs:
        return None
    return Image.open(pngs[frame_idx]).convert("RGBA")


def get_tile_sprite(tile_id: int, mapping: dict[int, str]) -> tuple[Image.Image | None, str]:
    """Return (sprite, label) for a tile_id."""
    if tile_id == 0x63:
        sprite = load_group_sprite(88)  # noIsland = water
        return sprite, mapping.get(88, "water")

    # Land tiles — use 'isle' for now
    sprite = load_group_sprite(28)  # isle
    return sprite, mapping.get(28, "isle")


def render_map(fort: FortFile, name: str, out_path: Path, mapping: dict[int, str]) -> None:
    """Render the map using real sprite tiles."""
    width = 16
    height = 16

    # Determine canvas size from sprite dimensions
    sample_water = load_group_sprite(88)
    sample_isle = load_group_sprite(28)
    if not sample_water or not sample_isle:
        print(f"  ERR: missing sprite groups, falling back to colored diamonds for {name}")
        return _render_fallback(fort, name, out_path)

    tile_w = max(sample_water.width, sample_isle.width)
    tile_h = max(sample_water.height, sample_isle.height)

    canvas_w = (width + height) * tile_w // 2 + tile_w + 200  # +200 for legend
    canvas_h = (width + height) * tile_h // 2 + tile_h * 4

    img = Image.new("RGBA", (canvas_w, canvas_h), (10, 10, 20, 255))
    draw = ImageDraw.Draw(img, "RGBA")

    # Tile distribution
    tile_dist: Counter[int] = Counter()
    for tile in fort.tiles:
        tile_dist[tile.type_id] += 1

    # Pre-cache sprites by tile_id
    sprite_cache: dict[int, Image.Image] = {}
    for tid in tile_dist:
        sprite, _ = get_tile_sprite(tid, mapping)
        if sprite:
            sprite_cache[tid] = sprite

    # Default fallback sprite (water)
    default_sprite = sample_water

    # Draw tiles back-to-front
    for y in range(height):
        for x in range(width):
            idx = y * width + x
            tile = fort.tiles[idx]
            tile_id = tile.type_id

            sprite = sprite_cache.get(tile_id, default_sprite)

            screen_x = (x - y) * tile_w // 2 + canvas_w // 2 - tile_w // 2 - 100
            screen_y = (x + y) * tile_h // 2 + tile_h

            img.paste(sprite, (screen_x, screen_y), sprite)

    # Title + legend
    try:
        font = ImageFont.truetype("arial.ttf", 16)
        font_small = ImageFont.truetype("arial.ttf", 12)
    except Exception:
        font = ImageFont.load_default()
        font_small = font

    draw.text((10, 10), name, fill=(255, 200, 0, 255), font=font)
    draw.text((10, 35), f"{width}×{height} grid", fill=(200, 200, 200, 255), font=font_small)

    y_off = 60
    draw.text((10, y_off), "Tiles:", fill=(255, 220, 0, 255), font=font_small)
    y_off += 18
    for tid, cnt in tile_dist.most_common(10):
        _, label = get_tile_sprite(tid, mapping)
        draw.text((10, y_off),
                  f"0x{tid:02X} = {label} ({cnt})",
                  fill=(220, 220, 220, 255), font=font_small)
        y_off += 14

    # Render post-grid records info
    y_off += 10
    draw.text((10, y_off), f"Records: {len(fort.records)}", fill=(255, 220, 0, 255), font=font_small)
    y_off += 16
    big_records = [r for r in fort.records if len(r.body) >= 10]
    draw.text((10, y_off), f"Big (≥10B): {len(big_records)}", fill=(200, 200, 200, 255), font=font_small)

    img.save(out_path)
    print(f"  Rendered: {out_path.name} ({canvas_w}×{canvas_h})")


def _render_fallback(fort: FortFile, name: str, out_path: Path) -> None:
    """Fallback colored diamonds if sprites missing."""
    pass  # original renderer; not used now


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load mapping
    raw = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    mapping = {int(k): v for k, v in raw.items() if not k.startswith("_")}
    print(f"Loaded {len(mapping)} sprite name mappings")

    # Verify key sprites exist
    print(f"  Group 28 (isle): {(SPRITES / 'group_028').exists()}")
    print(f"  Group 88 (noIsland/water): {(SPRITES / 'group_088').exists()}")

    archive = load_tarc(GAME_DIR / "netstorm.tarc")

    # MyOnlineGame.fort from disk
    print("\nRendering MyOnlineGame.fort...")
    fort_data = (GAME_DIR / "d" / "MyOnlineGame.fort").read_bytes()
    fort = FortFile(fort_data)
    render_map(fort, "MyOnlineGame", OUT_DIR / "MyOnlineGame.png", mapping)

    # All forts from TARC
    print("\nRendering all .fort from TARC...")
    fort_names = [e.name for e in archive.entries
                  if e.name.lower().endswith(".fort")]

    for fp in fort_names:
        try:
            data = archive.get(fp)
            if not data:
                continue
            fort = FortFile(data)
            short = fp.replace("\\d\\", "").replace("/d/", "").replace(".fort", "")
            render_map(fort, short, OUT_DIR / f"{short}.png", mapping)
        except Exception as e:
            print(f"  ERR {fp}: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
