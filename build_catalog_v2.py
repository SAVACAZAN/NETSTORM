"""
Build a much better visual catalog for sprites_all/.
- Shows atlas of each group (with frame count + biggest dimension)
- Filter by group ID
- Click to open full atlas image
- Linked to .type files where group_id is referenced (best-effort)
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent
EXTRACTED = ROOT / "extracted"
SPRITES = EXTRACTED / "sprites_all"
TYPES_DIR = EXTRACTED / "tarc_dump" / "d"


def parse_summary() -> list[tuple[int, int, tuple[int, int]]]:
    """Returns list of (group_id, frame_count, (max_w, max_h))."""
    summary_path = SPRITES / "summary.txt"
    if not summary_path.exists():
        return []
    out = []
    for line in summary_path.read_text().splitlines():
        m = re.match(r"\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)x(\d+)", line)
        if m:
            out.append((int(m.group(1)), int(m.group(2)),
                        (int(m.group(3)), int(m.group(4)))))
    return out


def collect_gif_refs() -> dict[str, list[str]]:
    """Collect all .gif references from .type files. Returns {gif_name: [type_files]}."""
    gif_refs: dict[str, list[str]] = {}
    if not TYPES_DIR.exists():
        return {}
    pattern = re.compile(r'"([a-zA-Z0-9_]+\.gif)"', re.IGNORECASE)
    for type_file in TYPES_DIR.glob("*.type"):
        try:
            text = type_file.read_text(errors="replace")
            for gif_name in set(pattern.findall(text)):
                gif_refs.setdefault(gif_name.lower(), []).append(type_file.name)
        except Exception:
            pass
    return gif_refs


def main() -> None:
    groups = parse_summary()
    gif_refs = collect_gif_refs()

    # Categorize groups by visual size
    def category(max_sz):
        w, h = max_sz
        area = w * h
        if area > 30000:
            return "huge"
        if area > 5000:
            return "large"
        if area > 1000:
            return "medium"
        return "small"

    cats = {"huge": [], "large": [], "medium": [], "small": []}
    for gi, n, sz in groups:
        cats[category(sz)].append((gi, n, sz))

    html = []
    html.append("""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<title>NetStorm Sprites Catalog v2</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
       background: #1a1a1a; color: #e0e0e0; padding: 20px; }
h1 { color: #ffaa00; border-bottom: 2px solid #ffaa00; padding-bottom: 10px; margin-bottom: 20px; }
h2 { color: #ffcc00; margin-top: 30px; margin-bottom: 15px; }
.stats { background: #2a2a2a; padding: 15px; border-radius: 6px; margin-bottom: 20px;
         display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }
.stats div { text-align: center; }
.stats strong { color: #ffaa00; font-size: 1.5em; display: block; }
.filter-bar { background: #2a2a2a; padding: 12px; border-radius: 6px;
              margin-bottom: 20px; display: flex; gap: 10px; align-items: center; }
.filter-bar input { padding: 8px; background: #1a1a1a; color: #e0e0e0;
                    border: 1px solid #444; border-radius: 4px; flex: 1; }
.filter-bar button { padding: 8px 16px; background: #ffaa00; color: #1a1a1a;
                     border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
.filter-bar button:hover { background: #ffcc00; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 15px; }
.card { background: #2a2a2a; border-radius: 6px; overflow: hidden;
        border: 1px solid #333; transition: border-color 0.2s; }
.card:hover { border-color: #ffaa00; }
.card-header { padding: 10px; background: #333; }
.card-header h3 { color: #ffaa00; margin: 0; font-size: 1.1em; }
.card-meta { font-size: 0.85em; color: #999; margin-top: 4px; }
.card-img { padding: 10px; text-align: center; min-height: 80px; }
.card-img img { max-width: 100%; max-height: 200px; image-rendering: pixelated;
                background: #111; padding: 4px; border-radius: 4px; }
.tag { display: inline-block; padding: 2px 8px; background: #444; border-radius: 12px;
       font-size: 0.75em; margin-right: 4px; }
.tag.huge { background: #c44; }
.tag.large { background: #c84; }
.tag.medium { background: #4a4; }
.tag.small { background: #44a; }
</style>
</head>
<body>
<h1>NetStorm Sprites — Catalog Vizual v2 (toate cele 6252 sprite-uri)</h1>
""")

    total_frames = sum(n for _, n, _ in groups)
    html.append(f"""
<div class="stats">
  <div><strong>{len(groups)}</strong>grupuri</div>
  <div><strong>{total_frames}</strong>frame-uri totale</div>
  <div><strong>{len(cats['huge']) + len(cats['large'])}</strong>grupuri mari (sprite-uri unități)</div>
  <div><strong>{len(gif_refs)}</strong>nume gif unice în .type files</div>
</div>

<div class="filter-bar">
  <input type="text" id="search" placeholder="Filtrează după group ID, dimensiune... (ex: 22, 121x152)">
  <button onclick="document.getElementById('search').value='';filter()">Reset</button>
</div>
""")

    # Order: huge, large, medium, small
    for cat_name, label in [("huge", "🐘 Sprite-uri uriașe (>30k pixeli)"),
                             ("large", "🐂 Sprite-uri mari (>5k pixeli — probabil unități/clădiri)"),
                             ("medium", "🐈 Sprite-uri medii (>1k pixeli — proiectile/efecte)"),
                             ("small", "🐀 Sprite-uri mici (UI/cursors/font)")]:
        items = cats[cat_name]
        if not items:
            continue
        html.append(f'<h2>{label} ({len(items)} grupuri)</h2>')
        html.append('<div class="grid">')
        for gi, n, sz in items:
            atlas_path = f"sprites_all/atlas_group_{gi:03d}.png"
            full_atlas = SPRITES / f"atlas_group_{gi:03d}.png"
            if not full_atlas.exists():
                continue
            html.append(f"""
<div class="card" data-gid="{gi}" data-size="{sz[0]}x{sz[1]}">
  <div class="card-header">
    <h3>Group {gi:03d}</h3>
    <div class="card-meta">
      <span class="tag {cat_name}">{sz[0]}×{sz[1]}</span>
      <span class="tag">{n} frames</span>
    </div>
  </div>
  <div class="card-img">
    <a href="{atlas_path}" target="_blank">
      <img src="{atlas_path}" alt="Group {gi}" loading="lazy">
    </a>
  </div>
</div>
""")
        html.append('</div>')

    html.append("""
<script>
function filter() {
  const q = document.getElementById('search').value.toLowerCase();
  for (const card of document.querySelectorAll('.card')) {
    const gid = card.dataset.gid;
    const size = card.dataset.size;
    const match = !q || gid.includes(q) || size.includes(q);
    card.style.display = match ? '' : 'none';
  }
}
document.getElementById('search').addEventListener('input', filter);
</script>
</body>
</html>
""")

    out_path = EXTRACTED / "catalog_v2.html"
    out_path.write_text("\n".join(html), encoding="utf-8")
    print(f"Generated: {out_path}")
    print(f"  {len(groups)} groups, {total_frames} frames")
    print(f"  Categories: huge={len(cats['huge'])}, large={len(cats['large'])}, "
          f"medium={len(cats['medium'])}, small={len(cats['small'])}")


if __name__ == "__main__":
    main()
