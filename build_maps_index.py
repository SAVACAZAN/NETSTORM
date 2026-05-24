"""Generate maps_index.html with thumbnails of all rendered .fort maps."""

from pathlib import Path

ROOT = Path(__file__).parent
MAPS_DIR = ROOT / "extracted" / "maps"
OUT = ROOT / "extracted" / "maps_index.html"

cards = []
for f in sorted(MAPS_DIR.glob("*.png")):
    name = f.stem
    cards.append(
        f'<div class="card"><h3>{name}</h3>'
        f'<a href="maps/{f.name}" target="_blank">'
        f'<img src="maps/{f.name}" alt="{name}" loading="lazy"></a></div>'
    )

html = f"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<title>NetStorm Maps</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: system-ui, sans-serif; background: #1a1a1a; color: #e0e0e0; padding: 20px; }}
h1 {{ color: #ffaa00; border-bottom: 2px solid #ffaa00; padding-bottom: 10px; margin-bottom: 20px; }}
.note {{ background: #332200; border-left: 4px solid #ffaa00; padding: 12px; margin-bottom: 20px;
        border-radius: 4px; line-height: 1.5; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 20px; }}
.card {{ background: #2a2a2a; border-radius: 6px; overflow: hidden; border: 1px solid #333;
        transition: transform 0.2s, border-color 0.2s; }}
.card:hover {{ transform: scale(1.02); border-color: #ffaa00; }}
.card h3 {{ padding: 10px 14px; background: #333; color: #ffcc00; font-size: 1em; }}
.card img {{ width: 100%; display: block; image-rendering: pixelated; }}
</style>
</head>
<body>
<h1>NetStorm — Toate mapele (.fort) randate izometric ({len(cards)} hărți)</h1>

<div class="note">
<strong>Note tehnice:</strong> Coloraje sunt heuristice (apa = albastru, sand = bej, restul = hash deterministic).<br>
Maparea reală <code>tile_id</code> → sprite-ul corespunzător va fi confirmată după extragere registry SHP.<br>
Format <code>.fort</code>: header 62B + grid 16×16×3B la offset <code>0x42</code> + records post-grid (length-prefixed).<br>
Click pe imagine pentru full-size.
</div>

<div class="grid">
{chr(10).join(cards)}
</div>
</body>
</html>
"""

OUT.write_text(html, encoding="utf-8")
print(f"Generated: {OUT}")
print(f"  {len(cards)} maps indexed")
