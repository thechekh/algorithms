"""The bit-level helpers agree with Python's own conversions, on every value that fits."""

import random
import struct

import numpy as np
import pytest

from bits_and_bytes import add_tenths, bits, float_parts, from_parts, negate, signed, utf8


def test_every_8_bit_value_round_trips():
    for v in range(-128, 128):
        pattern = bits(v, 8)
        assert signed(pattern) == v
        assert int(pattern, 2) == int.from_bytes(v.to_bytes(1, "big", signed=True), "big")


@pytest.mark.parametrize("width", [4, 8, 16, 32])
def test_negate_is_flip_and_add_one(width):
    rng = random.Random(width)
    for _ in range(500):
        v = rng.randrange(-(2 ** (width - 1)) + 1, 2 ** (width - 1))
        assert signed(negate(bits(v, width))) == -v
    lowest = bits(-(2 ** (width - 1)), width)
    assert negate(lowest) == lowest  # the one value with no positive partner


def test_float_parts_rebuild_the_float():
    rng = random.Random(0)
    for _ in range(2_000):
        x = rng.uniform(-1e6, 1e6) * 10.0 ** rng.randint(-30, 30)
        if x == 0:
            continue
        p = float_parts(x)
        assert from_parts(p["sign"], p["exponent"], p["fraction"]) == x
    assert int(float_parts(0.1)["bits"], 2) == int.from_bytes(struct.pack(">d", 0.1), "big") == 0x3FB999999999999A


def test_utf8_by_hand_matches_python_for_every_code_point():
    for cp in range(0x110000):
        if 0xD800 <= cp <= 0xDFFF:  # surrogates are reserved for UTF-16, not characters
            continue
        assert utf8(cp) == chr(cp).encode("utf-8")


def test_the_loops_in_add_tenths_are_plain_loops():
    n = 10_000
    total = 0.0
    total32 = np.float32(0)
    for _ in range(n):
        total += 0.1
        total32 = np.float32(total32 + np.float32(0.1))
    run = add_tenths(n)["results"]
    assert run["a loop, float64"] == total
    assert run["a loop, float32"] == float(total32)
