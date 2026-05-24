"""
Pattern scan for global terrain palette in netstorm.exe.

Heuristics:
- 768 bytes (256 RGB triples)
- Entry 0 = (0,0,0) black
- 150-256 unique colors (real palette, not random/zero data)
- Has blues (water tiles), greens (land), browns (terrain)
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter

EXE = Path(r"C:\Kits work\limaje de programare\9_GAMES\NetStorm-Islands-at-War_Win_EN_RIP-Version\NetStorm RIP\netstorm.exe")
OUT = Path(__file__).parent / "extracted" / "palette_candidates"


def color_distance(c1, c2):
    return abs(c1[0]-c2[0]) + abs(c1[1]-c2[1]) + abs(c1[2]-c2[2])


def is_plausible_palette(palette: bytes) -> dict | None:
    """Returns metrics if plausible, None if not."""
    if len(palette) != 768:
        return None

    # Entry 0 = black
    if palette[0] != 0 or palette[1] != 0 or palette[2] != 0:
        return None

    # Unique colors
    colors = []
    for i in range(0, 768, 3):
        colors.append((palette[i], palette[i+1], palette[i+2]))
    unique = set(colors)

    if len(unique) < 100 or len(unique) > 256:
        return None

    # Reject if first 16 entries are all zero or all 0xFF (junk)
    first_16 = palette[:48]
    if first_16 == b'\x00' * 48 or first_16 == b'\xff' * 48:
        return None

    # Count categories
    blues = sum(1 for c in colors if c[2] > 100 and c[0] < c[2] and c[1] < c[2])
    greens = sum(1 for c in colors if c[1] > 80 and c[0] < c[1] and c[2] < c[1])
    browns = sum(1 for c in colors if c[0] > 80 and c[1] < c[0] and c[2] < c[0] and c[2] < 100)
    grays = sum(1 for c in colors if abs(c[0]-c[1]) < 20 and abs(c[1]-c[2]) < 20 and 30 < c[0] < 220)

    # Real terrain palette has all categories
    if blues < 5 or greens < 5 or browns < 5:
        return None

    # Reject if too uniform (single hue family)
    if blues > 200 or greens > 200 or browns > 200:
        return None

    # Reject palettes where most colors are too close to each other (gradient junk)
    avg_color = (sum(c[0] for c in colors) / 256,
                 sum(c[1] for c in colors) / 256,
                 sum(c[2] for c in colors) / 256)
    diversity = sum(color_distance(c, avg_color) for c in colors) / 256
    if diversity < 50:  # too uniform
        return None

    return {
        "unique_colors": len(unique),
        "blues": blues,
        "greens": greens,
        "browns": browns,
        "grays": grays,
        "diversity": int(diversity),
    }


def main():
    print(f"Reading {EXE.name} ({EXE.stat().st_size:,} bytes)...")
    data = EXE.read_bytes()

    candidates = []
    print("Scanning for palette candidates (this takes ~30s)...")

    # Step 1 byte through entire binary
    for i in range(0, len(data) - 768):
        if data[i] == 0 and data[i+1] == 0 and data[i+2] == 0:  # quick filter
            metrics = is_plausible_palette(data[i:i+768])
            if metrics:
                candidates.append({"offset": i, **metrics})

    # Sort by score = unique * (blues + greens + browns) - similarity
    candidates.sort(
        key=lambda c: -(c["unique_colors"] + c["blues"] + c["greens"] + c["browns"] + c["diversity"])
    )

    print(f"\nFound {len(candidates)} plausible candidates.")
    print(f"Top 15:")
    print(f"{'#':<3} {'Offset':<12} {'Unique':<7} {'Blues':<6} {'Greens':<7} {'Browns':<7} {'Grays':<6} {'Div':<5}")
    for i, c in enumerate(candidates[:15]):
        print(f"{i:<3} 0x{c['offset']:08X}  {c['unique_colors']:<7} {c['blues']:<6} {c['greens']:<7} {c['browns']:<7} {c['grays']:<6} {c['diversity']:<5}")

    # Generate preview PNGs for top 5
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image
        for i, c in enumerate(candidates[:5]):
            offset = c["offset"]
            palette_bytes = data[offset:offset+768]
            img = Image.new("RGB", (16, 16))
            pixels = []
            for j in range(0, 768, 3):
                pixels.append((palette_bytes[j], palette_bytes[j+1], palette_bytes[j+2]))
            img.putdata(pixels)
            img_big = img.resize((256, 256), Image.NEAREST)
            out_path = OUT / f"candidate_{i:02d}_offset_{offset:08X}.png"
            img_big.save(out_path)
            # Save raw bytes too
            (OUT / f"candidate_{i:02d}_offset_{offset:08X}.bin").write_bytes(palette_bytes)
        print(f"\nGenerated {min(5, len(candidates))} preview PNGs in {OUT}")
    except ImportError:
        print("PIL not available, skipping previews")

    return candidates


if __name__ == "__main__":
    main()
