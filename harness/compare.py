"""
Differential comparison: original recording vs reimplementation replay.

For each tick, compares:
  - RNG state      (exact match required)
  - State hash     (exact match required once game logic is implemented)

Produces a DiffReport with per-tick results and summary statistics.

Usage:
    python -m harness.compare session.nsrec [--replay-output replay.json]
"""

from __future__ import annotations
import argparse
from dataclasses import dataclass, field
from pathlib import Path

from harness.formats import Recording
from harness.replay import ReplayResult, ReplaySnapshot, replay


@dataclass
class TickDiff:
    tick: int
    rng_match: bool
    rng_original: int
    rng_reimpl: int
    hash_match: bool
    hash_original: int
    hash_reimpl: int

    @property
    def ok(self) -> bool:
        return self.rng_match and self.hash_match

    def __str__(self) -> str:
        parts = [f"tick={self.tick:6d}"]
        if not self.rng_match:
            parts.append(f"RNG orig={self.rng_original:#010x} reimpl={self.rng_reimpl:#010x}")
        if not self.hash_match and self.hash_original != 0:
            parts.append(f"HASH orig={self.hash_original:#010x} reimpl={self.hash_reimpl:#010x}")
        return "  FAIL " + " | ".join(parts) if not self.ok else f"  ok   tick={self.tick}"


@dataclass
class DiffReport:
    total_ticks: int
    rng_matches: int
    hash_matches: int
    first_divergence: int | None   # tick number of first any mismatch
    diffs: list[TickDiff] = field(default_factory=list)

    @property
    def rng_parity(self) -> float:
        return self.rng_matches / self.total_ticks if self.total_ticks else 1.0

    @property
    def perfect(self) -> bool:
        return self.first_divergence is None

    def summary(self) -> str:
        lines = [
            f"Ticks compared : {self.total_ticks}",
            f"RNG parity     : {self.rng_parity:.2%}  ({self.rng_matches}/{self.total_ticks})",
            f"First diverge  : {'none' if self.perfect else f'tick {self.first_divergence}'}",
        ]
        return "\n".join(lines)


def compare(recording: Recording, replay_result: ReplayResult) -> DiffReport:
    diffs: list[TickDiff] = []
    rng_matches = 0
    hash_matches = 0
    first_div: int | None = None

    snap_by_tick: dict[int, ReplaySnapshot] = {s.tick: s for s in replay_result.snapshots}

    for frame in recording.frames:
        snap = snap_by_tick.get(frame.tick)
        if snap is None:
            continue

        rng_ok = frame.rng_state == 0 or (snap.rng_state == frame.rng_state)
        hash_ok = frame.state_hash == 0 or (snap.state_hash == frame.state_hash)

        if rng_ok:
            rng_matches += 1
        if hash_ok:
            hash_matches += 1

        diff = TickDiff(
            tick=frame.tick,
            rng_match=rng_ok,
            rng_original=frame.rng_state,
            rng_reimpl=snap.rng_state,
            hash_match=hash_ok,
            hash_original=frame.state_hash,
            hash_reimpl=snap.state_hash,
        )
        diffs.append(diff)

        if not diff.ok and first_div is None:
            first_div = frame.tick

    return DiffReport(
        total_ticks=len(diffs),
        rng_matches=rng_matches,
        hash_matches=hash_matches,
        first_divergence=first_div,
        diffs=diffs,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Compare recording vs reimplementation")
    ap.add_argument("recording", type=Path)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    rec = Recording.load(args.recording)
    result = replay(rec)
    report = compare(rec, result)

    print(report.summary())
    if args.verbose:
        for d in report.diffs:
            if not d.ok:
                print(d)

    raise SystemExit(0 if report.perfect else 1)


if __name__ == "__main__":
    main()
