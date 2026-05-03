"""Asset decoder smoke tests against real game files."""
import struct
from pathlib import Path

import pytest

ASSETS_DIR = Path(__file__).parents[2] / "netstorm" / "NetStorm RIP"
TARC_PATH  = ASSETS_DIR / "netstorm.tarc"
SHP_PATH   = ASSETS_DIR / "d" / "_shapes.shp"
CHFNT_PATH = ASSETS_DIR / "d" / "!Arial.normal.14.0.chfnt"
FORT_PATH  = ASSETS_DIR / "d" / "MyOnlineGame.fort"


def _skip_if_missing(path: Path):
    if not path.exists():
        pytest.skip(f"Asset not found: {path}")


# ---------------------------------------------------------------------------
# tarc
# ---------------------------------------------------------------------------

def test_tarc_loads_correct_count():
    _skip_if_missing(TARC_PATH)
    from netstorm.assets import tarc
    arch = tarc.load(TARC_PATH)
    assert len(arch.entries) == 258


def test_tarc_get_by_path():
    _skip_if_missing(TARC_PATH)
    from netstorm.assets import tarc
    arch = tarc.load(TARC_PATH)
    data = arch.get("d/!color.dat")
    assert data is not None and len(data) == 2304


def test_tarc_bulf_col_is_valid_palette():
    _skip_if_missing(TARC_PATH)
    from netstorm.assets import tarc
    arch = tarc.load(TARC_PATH)
    col = arch.get("d/bulf.col")
    assert col is not None
    # palette data: 8-byte header + 256*3 RGB = 776 bytes minimum
    assert len(col) >= 776
    # sanity: all RGB values fit in 0..255 (trivially true for bytes)


# ---------------------------------------------------------------------------
# shp
# ---------------------------------------------------------------------------

def test_shp_loads_without_hanging():
    _skip_if_missing(SHP_PATH)
    import time
    from netstorm.assets import shp
    t = time.time()
    dec = shp.load(SHP_PATH)
    assert time.time() - t < 5.0, "SHP decode took too long"


def test_shp_outer_group_count():
    _skip_if_missing(SHP_PATH)
    from netstorm.assets import shp
    dec = shp.load(SHP_PATH)
    assert len(dec.groups) >= 1
    assert len(dec.groups[0].frames) == 130


def test_shp_inner_groups():
    _skip_if_missing(SHP_PATH)
    from netstorm.assets import shp
    dec = shp.load(SHP_PATH)
    assert len(dec.groups) == 101   # 1 outer + 100 inner


def test_shp_outer_frame0_dimensions():
    _skip_if_missing(SHP_PATH)
    from netstorm.assets import shp
    dec = shp.load(SHP_PATH)
    f = dec.groups[0].frames[0]
    assert f.width  == 15
    assert f.height == 9
    assert f.pivot_x == 14
    assert f.pivot_y == 4


def test_shp_frame_pixel_data_size():
    _skip_if_missing(SHP_PATH)
    from netstorm.assets import shp
    dec = shp.load(SHP_PATH)
    for frame in dec.groups[0].frames:
        assert len(frame.data) == frame.width * frame.height
        assert len(frame.mask) == frame.width * frame.height


def test_shp_inner_frame_dimensions_plausible():
    _skip_if_missing(SHP_PATH)
    from netstorm.assets import shp
    dec = shp.load(SHP_PATH)
    for group in dec.groups[1:]:
        for f in group.frames:
            assert 1 <= f.width  <= 1024
            assert 1 <= f.height <= 1024


# ---------------------------------------------------------------------------
# chfnt
# ---------------------------------------------------------------------------

def test_chfnt_loads():
    _skip_if_missing(CHFNT_PATH)
    from netstorm.assets import chfnt
    font = chfnt.load(CHFNT_PATH)
    assert font.size == 14
    assert font.ascent == 11
    assert font.descent == 3


def test_chfnt_256_glyphs():
    _skip_if_missing(CHFNT_PATH)
    from netstorm.assets import chfnt
    font = chfnt.load(CHFNT_PATH)
    assert len(font.widths) == 256
    assert len(font.glyphs) == 256


def test_chfnt_advance_widths_plausible():
    _skip_if_missing(CHFNT_PATH)
    from netstorm.assets import chfnt
    font = chfnt.load(CHFNT_PATH)
    # W is typically the widest capital: wider than I
    assert font.get_width("W") > font.get_width("I")
    assert font.get_width("W") > font.get_width("i")
    # m is wide, i is narrow
    assert font.get_width("m") > font.get_width("i")
    # All widths fit in a reasonable pixel range for 14pt font
    for w in font.widths:
        assert 0 <= w <= 20, f"Unexpected width {w}"


# ---------------------------------------------------------------------------
# fort
# ---------------------------------------------------------------------------

def test_fort_loads_header():
    _skip_if_missing(FORT_PATH)
    from netstorm.assets import fort
    f = fort.FortFile.from_file(str(FORT_PATH))
    assert f.magic == 0x0046
    assert f.player_name == "Unnamed"


def test_fort_grid_is_16x16():
    _skip_if_missing(FORT_PATH)
    from netstorm.assets import fort
    f = fort.FortFile.from_file(str(FORT_PATH))
    assert len(f.tiles) == 256
    grid = f.tile_grid()
    assert grid.shape == (16, 16)


def test_fort_grid_is_mostly_water():
    """MyOnlineGame.fort is a fresh / blank fort - all 256 tiles should be water."""
    _skip_if_missing(FORT_PATH)
    from netstorm.assets import fort
    f = fort.FortFile.from_file(str(FORT_PATH))
    water_count = sum(1 for t in f.tiles if t.is_empty())
    assert water_count == 256, f"expected all water, got {water_count}/256"


def test_fort_record_stream_consumes_all_bytes():
    """Length-prefixed records (size:u16 + body) must walk exactly to EOF."""
    _skip_if_missing(FORT_PATH)
    from netstorm.assets import fort
    f = fort.FortFile.from_file(str(FORT_PATH))
    assert len(f.records) > 0, "expected at least one record"
    # Sum of record sizes must equal total bytes from SECTION_OFFSET to EOF.
    total = sum(r.size for r in f.records)
    expected = len(f.data) - fort.SECTION_OFFSET
    assert total == expected, f"records cover {total} bytes, expected {expected}"
    # Last record must end exactly at EOF.
    last = f.records[-1]
    assert last.offset + last.size == len(f.data)


def test_fort_record_sizes_are_valid():
    """Every record must have size >= 2 (includes the 2-byte size header)."""
    _skip_if_missing(FORT_PATH)
    from netstorm.assets import fort
    f = fort.FortFile.from_file(str(FORT_PATH))
    for r in f.records:
        assert r.size >= 2
        assert len(r.body) == r.size - 2


def test_fort_entity_record_count():
    """MyOnlineGame.fort has 3 'large' entity records (body size > 10)."""
    _skip_if_missing(FORT_PATH)
    from netstorm.assets import fort
    f = fort.FortFile.from_file(str(FORT_PATH))
    assert f.entity_count == 3
