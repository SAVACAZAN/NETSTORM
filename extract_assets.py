"""
NetStorm asset extraction script.

Dumps:
  - All TARC entries to extracted/tarc_dump/ (preserves sub-paths)
  - First 100 SHP frames as PNGs to extracted/sprites_png/
  - WAV listing JSON (no copies) to extracted/wav_listing/listing.json
  - Per-font ASCII alphabet preview PNGs to extracted/fonts_preview/
  - HTML catalog to extracted/catalog.html
  - INDEX.md report
"""

from __future__ import annotations
import sys
import os
import json
import struct
import wave
import logging
import contextlib
import traceback
from pathlib import Path

PROJECT_ROOT = Path(r"c:/Kits work/limaje de programare/9_GAMES/understandgame-master/understandgame-master")
NETSTORM_RIP = Path(r"c:/Kits work/limaje de programare/9_GAMES/NetStorm-Islands-at-War_Win_EN_RIP-Version/NetStorm RIP")

sys.path.insert(0, str(PROJECT_ROOT / "src"))

EXTRACTED = PROJECT_ROOT / "extracted"
TARC_DUMP = EXTRACTED / "tarc_dump"
SPRITES_PNG = EXTRACTED / "sprites_png"
WAV_LISTING = EXTRACTED / "wav_listing"
FONTS_PREVIEW = EXTRACTED / "fonts_preview"
ERRORS_LOG = EXTRACTED / "errors.log"

for d in (EXTRACTED, TARC_DUMP, SPRITES_PNG, WAV_LISTING, FONTS_PREVIEW):
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(ERRORS_LOG),
    filemode="w",
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("extract")
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(message)s"))
logging.getLogger().addHandler(console)
logging.getLogger().setLevel(logging.INFO)


def safe_name(name: str) -> Path:
    n = name.lstrip("\\/").replace("\\", "/")
    parts = []
    for p in n.split("/"):
        p = "".join(c for c in p if c.isprintable())
        p = p.replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_")
        if p:
            parts.append(p)
    return Path(*parts) if parts else Path("_unnamed")


def load_palette_from_archive(archive) -> list[tuple[int, int, int]]:
    """Load 256-entry palette from \\d\\bulf.col inside the TARC; fallback to grayscale."""
    col_data = archive.get("\\d\\bulf.col")
    if not col_data or len(col_data) < 8 + 256 * 3:
        log.warning("bulf.col not found or too short — using grayscale fallback")
        return [(i, i, i) for i in range(256)]
    palette = []
    for i in range(256):
        r, g, b = struct.unpack_from("BBB", col_data, 8 + i * 3)
        palette.append((r, g, b))
    return palette


def dump_tarc(archive, tarc_meta: list) -> None:
    log.info("Dumping TARC entries...")
    for entry in archive.entries:
        rel = safe_name(entry.name)
        out = TARC_DUMP / rel
        out.parent.mkdir(parents=True, exist_ok=True)

        # Use the raw extracted bytes (already-stored).  archive.get() applies
        # XOR for .type/.fort/.english/.cfg — write decrypted versions for
        # those, raw for everything else.
        try:
            data = archive.get(entry.name)
            if data is None:
                data = entry.data
            out.write_bytes(data)
        except Exception as e:
            log.error("TARC write fail %s: %s", entry.name, e)
            continue

        ext = out.suffix.lower().lstrip(".")
        tarc_meta.append({
            "name": entry.name,
            "size": entry.size,
            "ext": ext or "(no-ext)",
            "rel_path": str(rel).replace("\\", "/"),
        })


def dump_sprites(shp_path: Path, palette, max_frames: int = 100) -> list[dict]:
    from PIL import Image
    from netstorm.assets import shp as shp_mod

    log.info("Decoding _shapes.shp...")
    dec = shp_mod.load(shp_path)
    sprites_meta = []
    saved = 0

    flat = []
    for gi, group in enumerate(dec.groups):
        for fi, frame in enumerate(group.frames):
            flat.append((gi, fi, frame))

    log.info("Total frames decoded: %d (groups=%d). Saving first %d.",
             len(flat), len(dec.groups), max_frames)

    for gi, fi, frame in flat[:max_frames]:
        try:
            if frame.width <= 0 or frame.height <= 0:
                continue
            img = Image.new("RGBA", (frame.width, frame.height), (0, 0, 0, 0))
            px = img.load()
            for y in range(frame.height):
                for x in range(frame.width):
                    idx = y * frame.width + x
                    if frame.mask[idx]:
                        r, g, b = palette[frame.data[idx]]
                        px[x, y] = (r, g, b, 255)
            fname = f"g{gi:03d}_f{fi:03d}_{frame.width}x{frame.height}.png"
            out_path = SPRITES_PNG / fname
            img.save(out_path)
            sprites_meta.append({
                "file": fname,
                "group": gi,
                "frame_idx": fi,
                "w": frame.width,
                "h": frame.height,
                "pivot": [frame.pivot_x, frame.pivot_y],
                "bbox": list(frame.bbox),
            })
            saved += 1
        except Exception as e:
            log.error("Sprite g%d f%d: %s", gi, fi, e)

    log.info("Saved %d sprite PNGs.", saved)
    return sprites_meta


def list_wavs(sound_dir: Path) -> list[dict]:
    log.info("Indexing WAV files in %s ...", sound_dir)
    out = []
    for p in sorted(sound_dir.iterdir()):
        if p.suffix.lower() != ".wav":
            continue
        info = {
            "name": p.name,
            "size": p.stat().st_size,
            "abs_path": str(p).replace("\\", "/"),
        }
        try:
            with contextlib.closing(wave.open(str(p), "rb")) as w:
                info["channels"] = w.getnchannels()
                info["sample_rate"] = w.getframerate()
                info["sample_width"] = w.getsampwidth()
                info["frames"] = w.getnframes()
                info["duration_sec"] = round(w.getnframes() / float(w.getframerate()), 3) \
                    if w.getframerate() else None
        except Exception as e:
            log.warning("WAV header read fail %s: %s", p.name, e)
            info["error"] = str(e)
        out.append(info)
    log.info("Indexed %d WAVs.", len(out))
    return out


def render_font_preview(font_path: Path) -> dict | None:
    from PIL import Image
    try:
        from netstorm.assets import chfnt as chfnt_mod
    except Exception as e:
        log.error("chfnt import: %s", e)
        return None

    try:
        font = chfnt_mod.load(font_path)
    except Exception as e:
        log.error("chfnt load %s: %s", font_path.name, e)
        return None

    sample = "ABCDEFGHIJKLMNOPQRSTUVWXYZ\nabcdefghijklmnopqrstuvwxyz\n0123456789 .,!?:;'\"-+*/=()"
    canvas_w = 600
    canvas_h = max(font.size, 16) * 4 + 20

    # 2-bit grayscale palette: 0 transparent (background) else white
    pal = [(0, 0, 0)] * 256
    pal[0] = (255, 255, 255)  # if mask=1 and idx=0 → still white
    for i in range(1, 256):
        pal[i] = (255, 255, 255)

    img = Image.new("RGB", (canvas_w, canvas_h), (32, 32, 48))
    px = img.load()

    cursor_x, cursor_y = 4, 4
    line_h = max(font.ascent + font.descent, font.size, 14)

    for ch in sample:
        if ch == "\n":
            cursor_x = 4
            cursor_y += line_h
            continue
        glyph = font.get_glyph(ch)
        adv = font.get_width(ch)
        if glyph and glyph.width > 0 and glyph.height > 0:
            for y in range(glyph.height):
                for x in range(glyph.width):
                    idx = y * glyph.width + x
                    if glyph.mask[idx]:
                        gx = cursor_x + x
                        gy = cursor_y + y
                        if 0 <= gx < canvas_w and 0 <= gy < canvas_h:
                            px[gx, gy] = (235, 235, 245)
        cursor_x += adv if adv > 0 else (glyph.width if glyph else 6)
        if cursor_x > canvas_w - 20:
            cursor_x = 4
            cursor_y += line_h

    out_name = font_path.stem + ".png"
    out = FONTS_PREVIEW / out_name
    img.save(out)
    return {
        "file": out_name,
        "src": font_path.name,
        "size": font.size,
        "ascent": font.ascent,
        "descent": font.descent,
        "glyphs_total": sum(1 for g in font.glyphs if g is not None),
    }


def write_html_catalog(tarc_meta, sprites_meta, fonts_meta, wavs):
    html = []
    html.append("<!doctype html><html><head><meta charset='utf-8'>")
    html.append("<title>NetStorm Assets Catalog</title>")
    html.append("""<style>
body{font-family:Segoe UI,Arial,sans-serif;background:#1a1d22;color:#e0e0e0;margin:0;padding:0}
header{background:#2a2d35;padding:14px 22px;border-bottom:2px solid #3a8e3a}
h1{margin:0;font-size:20px}
nav{background:#22252b;padding:0 22px;border-bottom:1px solid #333}
nav button{background:#2a2d35;color:#ccc;border:0;padding:10px 18px;cursor:pointer;font-size:13px;margin-right:4px}
nav button.active{background:#3a8e3a;color:#fff}
.tab{display:none;padding:18px 22px}
.tab.active{display:block}
table{border-collapse:collapse;width:100%;font-size:12px}
th,td{padding:5px 9px;border-bottom:1px solid #333;text-align:left}
th{background:#2a2d35;position:sticky;top:0}
tr:hover{background:#2a2d35}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px}
.card{background:#2a2d35;border:1px solid #333;padding:6px;text-align:center;font-size:11px}
.card img{max-width:100%;background:#444;image-rendering:pixelated}
.font-preview img{background:#1a1d22;border:1px solid #333;display:block;margin:6px 0;max-width:100%}
audio{height:24px}
.stats{color:#8aff8a;margin:6px 0}
input[type=text]{background:#22252b;color:#e0e0e0;border:1px solid #333;padding:6px 10px;width:300px}
</style></head><body>""")

    html.append("<header><h1>NetStorm: Islands at War — Asset Catalog</h1>")
    html.append(f"<div class='stats'>{len(tarc_meta)} TARC entries · "
                f"{len(sprites_meta)} sprite PNGs · "
                f"{len(fonts_meta)} fonts · "
                f"{len(wavs)} WAVs</div></header>")

    html.append("<nav>")
    for i, t in enumerate(("TARC", "Sprites", "Fonts", "Sounds")):
        cls = "active" if i == 0 else ""
        html.append(f"<button class='{cls}' onclick=\"sw('{t.lower()}',this)\">{t}</button>")
    html.append("</nav>")

    # TARC
    html.append("<div id='tarc' class='tab active'>")
    html.append("<input type='text' placeholder='Filter...' oninput=\"filt('tarc-tbl', this.value)\"/>")
    html.append("<table id='tarc-tbl'><thead><tr><th>#</th><th>Name</th>"
                "<th>Size (B)</th><th>Ext</th><th>Path</th></tr></thead><tbody>")
    for i, e in enumerate(tarc_meta):
        href = f"tarc_dump/{e['rel_path']}"
        html.append(f"<tr><td>{i}</td><td><a href='{href}'>{e['name']}</a></td>"
                    f"<td>{e['size']:,}</td><td>{e['ext']}</td><td>{e['rel_path']}</td></tr>")
    html.append("</tbody></table></div>")

    # Sprites
    html.append("<div id='sprites' class='tab'><div class='grid'>")
    for s in sprites_meta:
        html.append(f"<div class='card'><img src='sprites_png/{s['file']}' alt='{s['file']}'/>"
                    f"<div>g{s['group']} f{s['frame_idx']}</div>"
                    f"<div>{s['w']}x{s['h']}</div></div>")
    html.append("</div></div>")

    # Fonts
    html.append("<div id='fonts' class='tab'>")
    for f in fonts_meta:
        html.append(f"<div class='font-preview'><b>{f['src']}</b> "
                    f"(size {f['size']}, ascent {f['ascent']}, descent {f['descent']}, "
                    f"glyphs {f['glyphs_total']}/256)<br>"
                    f"<img src='fonts_preview/{f['file']}'/></div>")
    html.append("</div>")

    # Sounds
    html.append("<div id='sounds' class='tab'>")
    html.append("<input type='text' placeholder='Filter...' oninput=\"filt('snd-tbl', this.value)\"/>")
    html.append("<table id='snd-tbl'><thead><tr><th>Name</th><th>Duration</th>"
                "<th>Rate</th><th>Ch</th><th>Size</th><th>Play</th></tr></thead><tbody>")
    for w in wavs:
        dur = w.get("duration_sec", "?")
        sr = w.get("sample_rate", "?")
        ch = w.get("channels", "?")
        path = w["abs_path"]
        html.append(f"<tr><td>{w['name']}</td><td>{dur}s</td><td>{sr}</td>"
                    f"<td>{ch}</td><td>{w['size']:,}</td>"
                    f"<td><audio controls preload='none' src='file:///{path}'></audio></td></tr>")
    html.append("</tbody></table></div>")

    # JS
    html.append("""<script>
function sw(id,btn){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  document.querySelectorAll('nav button').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
}
function filt(tblId,val){
  val=val.toLowerCase();
  const rows=document.querySelectorAll('#'+tblId+' tbody tr');
  rows.forEach(r=>{r.style.display=r.textContent.toLowerCase().includes(val)?'':'none';});
}
</script></body></html>""")

    out = EXTRACTED / "catalog.html"
    out.write_text("".join(html), encoding="utf-8")
    log.info("HTML catalog: %s", out)


def write_index_md(tarc_meta, sprites_meta, fonts_meta, wavs):
    # Top 10 largest TARC entries
    top = sorted(tarc_meta, key=lambda e: e["size"], reverse=True)[:10]
    # Extension stats
    ext_stats = {}
    for e in tarc_meta:
        ext_stats[e["ext"]] = ext_stats.get(e["ext"], 0) + 1
    ext_sorted = sorted(ext_stats.items(), key=lambda kv: -kv[1])
    # .fort files (any path containing .fort, decrypted from TARC + d/*.fort)
    forts_in_tarc = [e["name"] for e in tarc_meta if e["ext"] == "fort"]
    forts_in_d = sorted(p.name for p in NETSTORM_RIP.glob("d/*.fort"))

    lines = []
    lines.append("# NetStorm Asset Extraction — INDEX")
    lines.append("")
    lines.append("## Counts")
    lines.append(f"- **TARC entries:** {len(tarc_meta)}")
    lines.append(f"- **Sprite PNGs (first 100 frames):** {len(sprites_meta)}")
    lines.append(f"- **Fonts previewed:** {len(fonts_meta)}")
    lines.append(f"- **WAVs listed:** {len(wavs)}")
    lines.append("")
    lines.append("## Top 10 largest TARC entries")
    lines.append("| # | Name | Size (B) |")
    lines.append("|---|------|----------|")
    for i, e in enumerate(top, 1):
        lines.append(f"| {i} | `{e['name']}` | {e['size']:,} |")
    lines.append("")
    lines.append("## .fort maps")
    lines.append("**From TARC:**")
    if forts_in_tarc:
        for f in forts_in_tarc:
            lines.append(f"- `{f}`")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("**From d/ folder on disk:**")
    if forts_in_d:
        for f in forts_in_d:
            lines.append(f"- `{f}`")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Extension stats (TARC)")
    lines.append("| Extension | Count |")
    lines.append("|-----------|-------|")
    for ext, cnt in ext_sorted:
        lines.append(f"| `{ext}` | {cnt} |")
    lines.append("")
    (EXTRACTED / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")
    log.info("INDEX.md written.")


def main() -> int:
    try:
        from netstorm.assets import tarc as tarc_mod
    except Exception as e:
        log.error("Cannot import netstorm.assets.tarc: %s", e)
        return 1

    tarc_path = NETSTORM_RIP / "netstorm.tarc"
    if not tarc_path.exists():
        log.error("netstorm.tarc not found at %s", tarc_path)
        return 1

    log.info("Loading %s ...", tarc_path)
    archive = tarc_mod.load(tarc_path)
    log.info("TARC entries: %d", len(archive.entries))

    palette = load_palette_from_archive(archive)

    tarc_meta: list[dict] = []
    dump_tarc(archive, tarc_meta)

    sprites_meta: list[dict] = []
    shp_path = NETSTORM_RIP / "d" / "_shapes.shp"
    if shp_path.exists():
        try:
            sprites_meta = dump_sprites(shp_path, palette, max_frames=100)
        except Exception as e:
            log.error("SHP decode failed: %s\n%s", e, traceback.format_exc())
    else:
        log.warning("_shapes.shp not found at %s", shp_path)

    fonts_meta: list[dict] = []
    for fp in sorted((NETSTORM_RIP / "d").glob("*.chfnt")):
        meta = render_font_preview(fp)
        if meta:
            fonts_meta.append(meta)

    wavs = list_wavs(NETSTORM_RIP / "sound")
    (WAV_LISTING / "listing.json").write_text(json.dumps(wavs, indent=2), encoding="utf-8")

    write_html_catalog(tarc_meta, sprites_meta, fonts_meta, wavs)
    write_index_md(tarc_meta, sprites_meta, fonts_meta, wavs)

    # Quick on-screen summary
    log.info("DONE. extracted/ ready at %s", EXTRACTED)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
