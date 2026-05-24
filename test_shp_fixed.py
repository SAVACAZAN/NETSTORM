"""
Smoke test for the rewritten shp.py decoder.

Loads _shapes.shp, decodes the sunArcher frame 0, applies the dedicated
sunArcher palette extracted from netstorm.tarc (`d/sunarcher.col`), saves
the result as a PNG, and prints its SHA256 hash so the result can be
verified across runs.

Sun Archer is the first projectile/unit animation group AFTER the dude
group, i.e. groups[3] in the decoded list (groups[0]=outer UI sprites,
groups[1]=dude, groups[2]=banner pack, groups[3]=sunArcher).
"""

from __future__ import annotations
import hashlib
import sys
from pathlib import Path

# Make ``src`` importable when running this file directly.
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image  # noqa: E402

from netstorm.assets.shp import load  # noqa: E402
from netstorm.assets.tarc import load as tarc_load  # noqa: E402

NETSTORM_RIP = Path(
    r"C:\Kits work\limaje de programare\9_GAMES\NetStorm-Islands-at-War_Win_EN_RIP-Version\NetStorm RIP"
)
SHP_PATH = NETSTORM_RIP / "d" / "_shapes.shp"
TARC_PATH = NETSTORM_RIP / "netstorm.tarc"

# sunArcher group index in the decoded list (see groups[] preview above)
SUNARCHER_GROUP_IDX = 3
PALETTE_NAME = "sunarcher.col"

OUT_DIR = ROOT / "extracted"
OUT_DIR.mkdir(exist_ok=True)
OUT_PNG = OUT_DIR / "test_sunarcher_frame0.png"


def load_palette(tarc_path: Path, name: str) -> list[tuple[int, int, int]]:
    """Pull a .col 256-entry RGB palette from the .tarc archive."""
    arc = tarc_load(str(tarc_path))
    # Search for any entry whose path ends with the requested .col file.
    raw: bytes | None = None
    for entry_name in arc.names():
        if entry_name.lower().endswith(name.lower()):
            raw = arc.get(entry_name)
            break
    if raw is None or len(raw) < 768:
        # Fallback: identity grayscale so the script still produces an image
        return [(i, i, i) for i in range(256)]
    pal: list[tuple[int, int, int]] = []
    for i in range(256):
        r, g, b = raw[i * 3], raw[i * 3 + 1], raw[i * 3 + 2]
        pal.append((r, g, b))
    return pal


def main() -> int:
    if not SHP_PATH.exists():
        print(f"missing: {SHP_PATH}", file=sys.stderr)
        return 1

    shp = load(SHP_PATH)
    print(f"groups: {len(shp.groups)}")

    if SUNARCHER_GROUP_IDX >= len(shp.groups):
        print("sunArcher group out of range", file=sys.stderr)
        return 1

    group = shp.groups[SUNARCHER_GROUP_IDX]
    if not group.frames:
        print("sunArcher group has no frames", file=sys.stderr)
        return 1

    frame = group.frames[0]
    print(
        f"sunArcher frame 0: bbox={frame.width}x{frame.height} "
        f"canvas={frame.canvas_w}x{frame.canvas_h} "
        f"pivot=({frame.pivot_x},{frame.pivot_y}) "
        f"bbox_rel={frame.bbox}"
    )
    opaque = sum(frame.mask)
    print(f"opaque pixels: {opaque}/{frame.width * frame.height}")

    # Load palette (best-effort; falls back to grayscale).
    palette = (load_palette(TARC_PATH, PALETTE_NAME)
               if TARC_PATH.exists()
               else [(i, i, i) for i in range(256)])

    rgba = frame.to_rgba(palette)
    img = Image.frombytes("RGBA", (frame.width, frame.height), rgba)
    img.save(OUT_PNG)
    sha = hashlib.sha256(OUT_PNG.read_bytes()).hexdigest()
    print(f"wrote {OUT_PNG}")
    print(f"sha256: {sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
