"""
Extract ALL sprites from _shapes.shp grouped by inner-group.

Vechiul extract_assets.py extragea doar group 0 (UI/font 15x9 sprites).
Acesta extrage TOATE cele 202 grupuri (= 3000+ frames) cu organizare pe folder.

Output: extracted/sprites_all/group_NNN/frame_NNN.png
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image
from src.netstorm.assets.tarc import load as load_tarc
from src.netstorm.assets.shp import load as load_shp


GAME_DIR = Path(r"C:\Kits work\limaje de programare\9_GAMES\NetStorm-Islands-at-War_Win_EN_RIP-Version\NetStorm RIP")
OUT_DIR = Path(__file__).parent / "extracted" / "sprites_all"


def load_palette() -> list[tuple[int, int, int]]:
    archive = load_tarc(GAME_DIR / "netstorm.tarc")
    col_data = archive.get(r"\d\bulf.col")
    if not col_data:
        return [(i, i, i) for i in range(256)]
    pal = []
    for i in range(256):
        r, g, b = struct.unpack_from("BBB", col_data, 8 + i * 3)
        pal.append((r, g, b))
    return pal


def frame_to_png(frame, palette: list[tuple[int, int, int]], path: Path) -> None:
    rgba = frame.to_rgba(palette)
    img = Image.frombytes("RGBA", (frame.width, frame.height), rgba)
    img.save(path)


def make_group_atlas(frames, palette: list[tuple[int, int, int]], path: Path, max_per_row: int = 16) -> None:
    """Combine all frames in a group into a single horizontal/grid atlas image."""
    if not frames:
        return
    n = len(frames)
    rows = (n + max_per_row - 1) // max_per_row
    cols = min(n, max_per_row)
    cell_w = max(f.width for f in frames)
    cell_h = max(f.height for f in frames)
    atlas = Image.new("RGBA", (cell_w * cols, cell_h * rows), (0, 0, 0, 0))
    for i, frame in enumerate(frames):
        rgba = frame.to_rgba(palette)
        sub = Image.frombytes("RGBA", (frame.width, frame.height), rgba)
        atlas.paste(sub, ((i % max_per_row) * cell_w, (i // max_per_row) * cell_h), sub)
    atlas.save(path)


def main() -> None:
    print("Loading palette...")
    palette = load_palette()

    print("Loading SHP...")
    shp = load_shp(GAME_DIR / "d" / "_shapes.shp")
    shp.decode()
    print(f"  Total groups: {len(shp.groups)}")
    print(f"  Total frames: {sum(len(g.frames) for g in shp.groups)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    summary = []

    for gi, group in enumerate(shp.groups):
        if not group.frames:
            continue

        gdir = OUT_DIR / f"group_{gi:03d}"
        gdir.mkdir(exist_ok=True)

        sizes = []
        for fi, frame in enumerate(group.frames):
            png_path = gdir / f"frame_{fi:03d}_{frame.width}x{frame.height}.png"
            try:
                frame_to_png(frame, palette, png_path)
                sizes.append((frame.width, frame.height))
            except Exception as e:
                print(f"  ERR group {gi} frame {fi}: {e}")

        # atlas pentru navigare rapidă
        atlas_path = OUT_DIR / f"atlas_group_{gi:03d}.png"
        try:
            make_group_atlas(group.frames, palette, atlas_path)
        except Exception as e:
            print(f"  ERR atlas group {gi}: {e}")

        if sizes:
            max_sz = max(sizes, key=lambda s: s[0] * s[1])
            summary.append((gi, len(group.frames), max_sz))

    print(f"\nGenerated {sum(1 for _ in OUT_DIR.glob('group_*/*.png'))} PNG files")
    print(f"Generated {sum(1 for _ in OUT_DIR.glob('atlas_*.png'))} atlas images")

    # Summary
    print("\nTop 20 groups by largest frame:")
    for gi, n, max_sz in sorted(summary, key=lambda x: -x[2][0] * x[2][1])[:20]:
        print(f"  Group {gi:3d}: {n:3d} frames, biggest {max_sz[0]}x{max_sz[1]}")

    # Save summary file for catalog
    summary_path = OUT_DIR / "summary.txt"
    with summary_path.open("w") as f:
        f.write(f"Total groups with frames: {len(summary)}\n")
        f.write(f"Total frames: {sum(s[1] for s in summary)}\n\n")
        f.write("group_id | frame_count | max_size\n")
        f.write("-" * 40 + "\n")
        for gi, n, max_sz in summary:
            f.write(f"{gi:3d} | {n:3d} | {max_sz[0]}x{max_sz[1]}\n")
    print(f"\nSummary saved to {summary_path}")


if __name__ == "__main__":
    main()
