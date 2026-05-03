"""
Replay a .nsrec recording through the Python reimplementation.

Feeds each frame's input_mask and rng_state into the reimplementation
in lock-step, producing a sequence of state snapshots for comparison.
"""

from __future__ import annotations
import argparse
from dataclasses import dataclass, field
from pathlib import Path

from harness.formats import Recording, RecFrame
from netstorm.engine.rng import RNG
from netstorm.game.world import World


class _NullRegistry:
    """Stub TypeRegistry for replay — World.tick() never queries types."""
    def get(self, name: str):
        return None


@dataclass
class ReplaySnapshot:
    tick: int
    rng_state: int
    state_hash: int   # FNV-32 of reimplementation's game state struct


@dataclass
class ReplayResult:
    recording: Recording
    snapshots: list[ReplaySnapshot] = field(default_factory=list)


def replay(recording: Recording) -> ReplayResult:
    """
    Drive the reimplementation from a recording, producing snapshots
    at every tick for differential comparison.
    """
    rng = RNG(seed=recording.header.rng_seed)
    world = World(types=_NullRegistry(), rng=rng)
    result = ReplayResult(recording=recording)

    for frame in recording.frames:
        # Check RNG sync BEFORE this tick's game logic (frame.rng_state is pre-tick)
        if frame.rng_state and rng.state != frame.rng_state:
            print(f"  [warn] tick {frame.tick}: RNG diverged "
                  f"(expected {frame.rng_state:#010x}, got {rng.state:#010x})")

        # Apply inputs (stubbed — no input system yet)
        _apply_inputs(frame)

        # Run one game tick
        world.tick()

        # Snapshot taken after tick
        snap = ReplaySnapshot(
            tick=frame.tick,
            rng_state=rng.state,
            state_hash=world.state.compute_hash(),
        )
        result.snapshots.append(snap)

    return result


def _apply_inputs(frame: RecFrame) -> None:
    # TODO: feed frame.input_mask + frame.mouse_x/y into input system
    pass


def main() -> None:
    ap = argparse.ArgumentParser(description="Replay a .nsrec recording")
    ap.add_argument("recording", type=Path)
    ap.add_argument("--output", type=Path, help="save replay snapshots as JSON")
    args = ap.parse_args()

    rec = Recording.load(args.recording)
    print(f"Loaded recording: {len(rec.frames)} frames, seed={rec.header.rng_seed:#010x}")
    result = replay(rec)
    print(f"Replay done: {len(result.snapshots)} snapshots")

    if args.output:
        import json
        data = [{"tick": s.tick, "rng": s.rng_state, "hash": s.state_hash}
                for s in result.snapshots]
        args.output.write_text(json.dumps(data, indent=2))
        print(f"Saved snapshots → {args.output}")


if __name__ == "__main__":
    main()
