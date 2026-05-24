"""
Re-extract sprites using the CORRECT per-group palette.

Discovery: each unit type has its own .col file in TARC.
The previous extraction used bulf.col globally — wrong for non-bulf units.

Mapping convention (from .type files): name "altar" -> palette ".col" with same/similar name.
We try multiple naming conventions to find a match.
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image
from src.netstorm.assets.tarc import load as load_tarc
from src.netstorm.assets.shp import load as load_shp


GAME_DIR = Path(r"C:\Kits work\limaje de programare\9_GAMES\NetStorm-Islands-at-War_Win_EN_RIP-Version\NetStorm RIP")
ROOT = Path(__file__).parent
EXTRACTED = ROOT / "extracted"
OUT_DIR = EXTRACTED / "sprites_palette_correct"
MAPPING_PATH = EXTRACTED / "sprite_name_mapping.json"


def parse_palette(col_data: bytes) -> list[tuple[int, int, int]]:
    """Parse .col file: 8-byte header + 256 RGB triples."""
    pal = []
    for i in range(256):
        r, g, b = struct.unpack_from("BBB", col_data, 8 + i * 3)
        pal.append((r, g, b))
    return pal


def find_palette(archive, group_name: str) -> str | None:
    """Try to find a .col file matching the sprite name."""
    name_lower = group_name.lower()

    # Direct match
    candidates = [
        f"\\d\\{name_lower}.col",
        f"\\d\\{group_name}.col",
    ]

    for c in candidates:
        if archive.get(c):
            return c

    # Substring match: e.g. "sunArcher" -> "sunarcher.col"
    for entry in archive.entries:
        if entry.name.lower().endswith(".col"):
            base = entry.name.lower().replace("\\d\\", "").replace(".col", "")
            if base == name_lower:
                return entry.name
            # Common variants
            if base.replace(" ", "") == name_lower.replace(" ", ""):
                return entry.name

    # Try removing "sun"/"rain"/"thunder"/"wind" prefix and match
    for prefix in ["sun", "rain", "thunder", "wind"]:
        if name_lower.startswith(prefix):
            stripped = name_lower[len(prefix):]
            for entry in archive.entries:
                bn = entry.name.lower().replace("\\d\\", "").replace(".col", "")
                if bn == stripped:
                    return entry.name

    return None


def main() -> None:
    print("Loading mapping...")
    raw = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    mapping = {int(k): v for k, v in raw.items() if not k.startswith("_")}
    print(f"  {len(mapping)} groups in mapping")

    print("Loading TARC...")
    archive = load_tarc(GAME_DIR / "netstorm.tarc")

    # Cache palettes
    palette_cache: dict[str, list] = {}

    # Bulf as fallback
    fallback_pal = parse_palette(archive.get("\\d\\bulf.col"))

    print("Loading SHP...")
    shp = load_shp(GAME_DIR / "d" / "_shapes.shp")
    shp.decode()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build palette mapping table
    palette_map: dict[int, str] = {}  # group_id -> .col file path
    summary = []

    print("\nMatching palettes:")
    for gi, name in mapping.items():
        col_path = find_palette(archive, name)
        if col_path:
            palette_map[gi] = col_path
        summary.append((gi, name, col_path or "(fallback: bulf.col)"))

    # Print first 30 matches for visibility
    matched = sum(1 for _, _, p in summary if "fallback" not in p)
    print(f"  Matched: {matched}/{len(summary)} groups")
    print("\n  First 30:")
    for gi, name, pal in summary[:30]:
        marker = "*" if "fallback" not in pal else "."
        print(f"  {marker} group {gi:3d} = {name:30s} -> {pal}")

    print("\nExtracting with correct palettes...")
    for gi, group in enumerate(shp.groups):
        if not group.frames:
            continue

        col_path = palette_map.get(gi)
        if col_path:
            if col_path not in palette_cache:
                palette_cache[col_path] = parse_palette(archive.get(col_path))
            palette = palette_cache[col_path]
        else:
            palette = fallback_pal

        # Save first 4 frames + atlas
        gdir = OUT_DIR / f"group_{gi:03d}_{mapping.get(gi, 'unknown')}"
        gdir.mkdir(exist_ok=True)

        for fi, frame in enumerate(group.frames[:8]):  # save first 8 frames
            try:
                rgba = frame.to_rgba(palette)
                img = Image.frombytes("RGBA", (frame.width, frame.height), rgba)
                img.save(gdir / f"frame_{fi:03d}.png")
            except Exception as e:
                pass

        # Build atlas of first row only (for compactness)
        if group.frames:
            n = min(len(group.frames), 16)
            cell_w = max(f.width for f in group.frames[:n])
            cell_h = max(f.height for f in group.frames[:n])
            atlas = Image.new("RGBA", (cell_w * n, cell_h), (0, 0, 0, 0))
            for i, frame in enumerate(group.frames[:n]):
                try:
                    rgba = frame.to_rgba(palette)
                    sub = Image.frombytes("RGBA", (frame.width, frame.height), rgba)
                    atlas.paste(sub, (i * cell_w, 0), sub)
                except Exception:
                    pass
            atlas.save(OUT_DIR / f"atlas_{gi:03d}_{mapping.get(gi, 'unknown')}.png")

    print(f"\nDone. Output: {OUT_DIR}")
    print(f"Atlases: {len(list(OUT_DIR.glob('atlas_*.png')))}")

    # Save palette map for posterity
    pal_map_out = {str(k): v for k, v in palette_map.items()}
    (OUT_DIR / "palette_map.json").write_text(
        json.dumps(pal_map_out, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
