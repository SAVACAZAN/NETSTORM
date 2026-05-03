"""
RNG parity tests.

Once we RE the actual RNG from netstorm.exe, we capture a known sequence
(seed → first N outputs) from the original and add it as a fixture here.
The test must pass exactly — any drift means behavioral divergence.
"""

import pytest
from netstorm.engine.rng import RNG, RAND_MAX


def test_rng_range():
    rng = RNG(seed=1)
    for _ in range(1000):
        v = rng.rand()
        assert 0 <= v <= RAND_MAX


def test_rng_deterministic():
    a = RNG(seed=42)
    b = RNG(seed=42)
    seq_a = [a.rand() for _ in range(100)]
    seq_b = [b.rand() for _ in range(100)]
    assert seq_a == seq_b


def test_rng_different_seeds():
    a = RNG(seed=1)
    b = RNG(seed=2)
    assert [a.rand() for _ in range(10)] != [b.rand() for _ in range(10)]


def test_rng_snapshot_restore():
    rng = RNG(seed=1337)
    _ = [rng.rand() for _ in range(50)]
    state = rng.snapshot()
    seq_after = [rng.rand() for _ in range(20)]

    rng2 = RNG(seed=0)
    rng2.restore(state)
    assert [rng2.rand() for _ in range(20)] == seq_after


# Known sequence confirmed: netstorm.exe uses standard MSVC CRT rand()
# (multiplier 0x343FD, addend 0x269EC3) — RE confirmed at 0xF179D.
# These values are the canonical MSVC output for seed=1.
KNOWN_SEQUENCE_SEED = 1
KNOWN_SEQUENCE = [
    41, 18467, 6334, 26500, 19169, 15724, 11478, 29358, 26962, 24464,
    5705, 28145, 23281, 16827, 9961, 491, 2995, 11942, 4827, 5436,
]


def test_rng_known_sequence():
    rng = RNG(seed=KNOWN_SEQUENCE_SEED)
    for i, expected in enumerate(KNOWN_SEQUENCE):
        got = rng.rand()
        assert got == expected, f"call {i+1}: expected {expected}, got {got}"
