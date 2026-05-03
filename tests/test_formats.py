"""Tests for .nsrec recording format (roundtrip serialization)."""

import io
import time
from harness.formats import (
    InputBit, RecFlags, RecFrame, RecHeader, Recording
)


def _make_header() -> RecHeader:
    return RecHeader(
        flags=RecFlags.HAS_RNG,
        rng_seed=0xDEADBEEF,
        map_id=3,
        player_id=0,
        tick_rate=15.0,
        start_ts=int(time.time() * 1000),
    )


def test_header_roundtrip():
    h = _make_header()
    h2 = RecHeader.unpack(h.pack())
    assert h2.rng_seed == h.rng_seed
    assert h2.map_id == h.map_id
    assert h2.tick_rate == h.tick_rate


def test_frame_roundtrip():
    f = RecFrame(tick=42, input_mask=InputBit.MOUSE_L, mouse_x=320, mouse_y=240,
                 rng_state=0x12345678, state_hash=0xABCDEF01, net_data=b"hello")
    packed = f.pack()
    buf = io.BytesIO(packed)
    f2 = RecFrame.unpack_from(buf)
    assert f2.tick == 42
    assert f2.mouse_x == 320
    assert f2.rng_state == 0x12345678
    assert f2.net_data == b"hello"


def test_recording_roundtrip(tmp_path):
    rec = Recording(header=_make_header())
    for i in range(100):
        rec.append(RecFrame(tick=i, input_mask=InputBit(0), rng_state=i * 7))
    path = tmp_path / "test.nsrec"
    rec.save(path)

    loaded = Recording.load(path)
    assert len(loaded.frames) == 100
    assert loaded.frames[50].rng_state == 50 * 7
    assert loaded.header.rng_seed == 0xDEADBEEF


def test_crc_corruption_detected(tmp_path):
    import pytest
    rec = Recording(header=_make_header())
    rec.append(RecFrame(tick=0, input_mask=InputBit(0)))
    path = tmp_path / "corrupt.nsrec"
    rec.save(path)

    data = bytearray(path.read_bytes())
    data[40] ^= 0xFF  # flip a byte in first frame
    path.write_bytes(data)

    with pytest.raises(ValueError, match="CRC"):
        Recording.load(path)
