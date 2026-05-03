"""
Differential parity tests.

Each .nsrec file in tests/differential/recordings/ is replayed through
the reimplementation and compared tick-by-tick against the original.

To add a new test case:
  1. Run: python -m harness.record --output tests/differential/recordings/my_session.nsrec
  2. The test is picked up automatically.

A test passes only if DiffReport.perfect == True (zero divergence on
all captured metrics: RNG state, state hash).
"""

import pytest
from pathlib import Path

from harness.formats import Recording
from harness.replay import replay
from harness.compare import compare

RECORDINGS_DIR = Path(__file__).parent / "recordings"


def _recording_files():
    return sorted(RECORDINGS_DIR.glob("*.nsrec"))


@pytest.mark.parametrize("rec_path", _recording_files(), ids=lambda p: p.stem)
def test_differential_parity(rec_path: Path):
    recording = Recording.load(rec_path)
    result = replay(recording)
    report = compare(recording, result)

    if not report.perfect:
        failing = [d for d in report.diffs if not d.ok]
        details = "\n".join(str(d) for d in failing[:20])
        pytest.fail(
            f"Diverged at tick {report.first_divergence} "
            f"({len(failing)}/{report.total_ticks} ticks failed)\n{details}"
        )


def test_no_recordings_is_ok():
    """Passes trivially when no recordings exist yet — serves as a placeholder."""
    files = _recording_files()
    if not files:
        pytest.skip("No .nsrec recordings yet — record one with: python -m harness.record")
