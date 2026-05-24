"""
Build a sprite catalog with REAL names (from sprite_name_mapping.json).

Groups now show "Group 95 = altar" instead of just "Group 095".
Categories regrouped by gameplay function (terrain, buildings, units, projectiles, FX, UI).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
EXTRACTED = ROOT / "extracted"
SPRITES = EXTRACTED / "sprites_palette_correct"
SUMMARY_DIR = EXTRACTED / "sprites_all"  # summary.txt still here
MAPPING_PATH = EXTRACTED / "sprite_name_mapping.json"


def load_mapping() -> dict[int, str]:
    raw = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    return {int(k): v for k, v in raw.items() if not k.startswith("_")}


def parse_summary() -> list[tuple[int, int, tuple[int, int]]]:
    summary_path = SUMMARY_DIR / "summary.txt"
    out = []
    for line in summary_path.read_text().splitlines():
        m = re.match(r"\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)x(\d+)", line)
        if m:
            out.append((int(m.group(1)), int(m.group(2)),
                        (int(m.group(3)), int(m.group(4)))))
    return out


def categorize(name: str, max_sz: tuple[int, int]) -> str:
    """Heuristic category from name + size."""
    n = name.lower()
    w, h = max_sz

    # Terrain
    if any(k in n for k in ["isle", "island", "fringe", "edge", "noisland"]):
        return "terrain"

    # Buildings (factories, batteries, blockers, geysers, altars)
    if any(k in n for k in ["factory", "battery", "blocker", "geyser", "altar",
                             "bridge", "fence", "embassy", "residence", "dais",
                             "treeoneonecturer", "tree", "buildings", "vegetation"]):
        return "building"

    # Units (walkers, archers, flyers, bombers)
    if any(k in n for k in ["archer", "flyer", "walker", "balloon", "aviary",
                             "cannon", "disc", "dude", "priest", "bulf", "buried",
                             "trooper", "thunderlord", "manaman"]):
        return "unit"

    # Projectiles & explosions
    if any(k in n for k in ["bomb", "bolt", "missile", "manabolt", "flare",
                             "explode", "explosion"]):
        return "projectile"

    # FX
    if any(k in n for k in ["forcefield", "shield", "smoke", "fire", "particle",
                             "rain", "lightning"]):
        return "fx"

    # UI
    if "ui_" in n or n in ("banner",):
        return "ui"

    # Size-based fallback
    area = w * h
    if area > 20000:
        return "background"
    if area < 500:
        return "ui"
    return "other"


CATEGORY_LABELS = {
    "terrain": "🏝️ Teren (insule, ape, margini)",
    "building": "🏛️ Clădiri (turnuri, geyseri, altare, fabrici)",
    "unit": "⚔️ Unități (walker, archer, flyer)",
    "projectile": "💥 Proiectile & Explozii",
    "fx": "✨ Efecte vizuale (rain, lightning, shields)",
    "ui": "🖼️ UI (font, butoane)",
    "background": "🌅 Background-uri",
    "other": "❓ Altele",
}


def main() -> None:
    mapping = load_mapping()
    summary = parse_summary()

    # Build full info
    items = []
    for gi, n_frames, max_sz in summary:
        name = mapping.get(gi, f"unknown_{gi}")
        cat = categorize(name, max_sz)
        items.append({
            "gi": gi,
            "name": name,
            "frames": n_frames,
            "size": max_sz,
            "cat": cat,
        })

    # Group by category
    by_cat: dict[str, list] = {k: [] for k in CATEGORY_LABELS}
    for item in items:
        by_cat[item["cat"]].append(item)

    # Sort each category by frame count desc (most-animated first)
    for cat_items in by_cat.values():
        cat_items.sort(key=lambda x: -x["frames"])

    # Build HTML
    html = ['<!DOCTYPE html>',
            '<html lang="ro"><head><meta charset="UTF-8">',
            '<title>NetStorm Sprites — Cu Nume Reale</title>',
            '<style>',
            '* { box-sizing: border-box; margin: 0; padding: 0; }',
            'body { font-family: system-ui, sans-serif; background: #0f1419; color: #e0e0e0; padding: 20px; }',
            'h1 { color: #ffaa00; border-bottom: 2px solid #ffaa00; padding-bottom: 10px; margin-bottom: 16px; }',
            'h2 { color: #ffcc00; margin: 28px 0 12px; }',
            '.stats { background: #1a2030; padding: 14px; border-radius: 6px; margin-bottom: 18px; '
            'display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }',
            '.stats div { text-align: center; padding: 8px; }',
            '.stats strong { color: #ffaa00; font-size: 1.4em; display: block; }',
            '.filter-bar { background: #1a2030; padding: 12px; border-radius: 6px; '
            'margin-bottom: 18px; display: flex; gap: 10px; }',
            '.filter-bar input { padding: 8px 12px; background: #0f1419; color: #e0e0e0; '
            'border: 1px solid #444; border-radius: 4px; flex: 1; font-size: 14px; }',
            '.filter-bar button { padding: 8px 16px; background: #ffaa00; color: #0f1419; '
            'border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }',
            '.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }',
            '.card { background: #1a2030; border-radius: 6px; overflow: hidden; '
            'border: 1px solid #2a3040; transition: all 0.2s; }',
            '.card:hover { border-color: #ffaa00; transform: translateY(-2px); }',
            '.card-header { padding: 8px 12px; background: #232a3a; border-bottom: 1px solid #2a3040; }',
            '.card-name { color: #ffcc00; font-weight: bold; font-size: 1em; word-break: break-all; }',
            '.card-meta { color: #888; font-size: 0.78em; margin-top: 3px; }',
            '.tag { display: inline-block; padding: 1px 6px; background: #2a3040; '
            'border-radius: 8px; font-size: 0.7em; margin-right: 3px; }',
            '.card-img { padding: 8px; text-align: center; min-height: 80px; '
            'display: flex; align-items: center; justify-content: center; }',
            '.card-img img { max-width: 100%; max-height: 180px; image-rendering: pixelated; '
            'background: #050810; padding: 4px; border-radius: 4px; }',
            '</style></head><body>',
            f'<h1>NetStorm Sprites — Catalog cu Nume Reale ({len(items)} grupuri)</h1>']

    total_frames = sum(i["frames"] for i in items)
    cat_counts = {k: len(v) for k, v in by_cat.items() if v}
    html.append('<div class="stats">')
    html.append(f'<div><strong>{len(items)}</strong>grupuri totale</div>')
    html.append(f'<div><strong>{total_frames}</strong>frame-uri</div>')
    for cat, count in cat_counts.items():
        html.append(f'<div><strong>{count}</strong>{CATEGORY_LABELS[cat].split(" ", 1)[1]}</div>')
    html.append('</div>')

    html.append('<div class="filter-bar">')
    html.append('<input type="text" id="search" placeholder="🔎 Caută după nume (ex: altar, walker, isle, geyser)...">')
    html.append('<button onclick="document.getElementById(\'search\').value=\'\';filter()">Reset</button>')
    html.append('</div>')

    for cat, label in CATEGORY_LABELS.items():
        cat_items = by_cat[cat]
        if not cat_items:
            continue
        html.append(f'<h2>{label} ({len(cat_items)} grupuri)</h2>')
        html.append('<div class="grid">')
        for item in cat_items:
            atlas_path = f"sprites_palette_correct/atlas_{item['gi']:03d}_{item['name']}.png"
            sample_path = atlas_path
            html.append(
                f'<div class="card" data-name="{item["name"].lower()}" '
                f'data-gid="{item["gi"]}">'
                f'<div class="card-header">'
                f'<div class="card-name">{item["name"]}</div>'
                f'<div class="card-meta">'
                f'<span class="tag">grup {item["gi"]:03d}</span>'
                f'<span class="tag">{item["frames"]} fr.</span>'
                f'<span class="tag">{item["size"][0]}×{item["size"][1]}</span>'
                f'</div></div>'
                f'<div class="card-img">'
                f'<a href="{atlas_path}" target="_blank">'
                f'<img src="{atlas_path}" alt="{item["name"]}" loading="lazy">'
                f'</a></div></div>'
            )
        html.append('</div>')

    html.append('''<script>
function filter() {
  const q = document.getElementById('search').value.toLowerCase();
  for (const card of document.querySelectorAll('.card')) {
    const match = !q || card.dataset.name.includes(q) || card.dataset.gid.includes(q);
    card.style.display = match ? '' : 'none';
  }
  // Hide empty section headers
  for (const h2 of document.querySelectorAll('h2')) {
    const grid = h2.nextElementSibling;
    if (grid && grid.classList.contains('grid')) {
      const visible = [...grid.children].some(c => c.style.display !== 'none');
      h2.style.display = visible ? '' : 'none';
      grid.style.display = visible ? '' : 'none';
    }
  }
}
document.getElementById('search').addEventListener('input', filter);
</script>
</body></html>''')

    out_path = EXTRACTED / "catalog_named.html"
    out_path.write_text("\n".join(html), encoding="utf-8")
    print(f"Generated: {out_path}")
    print(f"  {len(items)} groups categorized")
    for cat, n in cat_counts.items():
        print(f"  {cat}: {n}")


if __name__ == "__main__":
    main()
