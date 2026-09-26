"""The correct searches agree with a plain scan and with the standard library; each
classic bug is caught by one small case."""

import bisect
import random

import pytest

from binary_search import (
    binary_search,
    bisect_left,
    bug_misses_the_last_one,
    bug_never_finishes,
    bug_reads_past_the_end,
)


def scan(items, target):
    return items.index(target) if target in items else -1


@pytest.mark.parametrize("seed", range(200))
def test_matches_a_plain_scan(seed):
    rng = random.Random(seed)
    items = sorted(rng.sample(range(-50, 50), rng.randint(0, 40)))
    for target in range(-55, 55):
        assert binary_search(items, target) == scan(items, target)


@pytest.mark.parametrize("seed", range(200))
def test_bisect_left_matches_the_standard_library(seed):
    rng = random.Random(seed)
    items = sorted(rng.choices(range(-20, 20), k=rng.randint(0, 40)))  # duplicates included
    for target in range(-25, 25):
        assert bisect_left(items, target) == bisect.bisect_left(items, target)


def test_the_ends_and_the_empty_list():
    assert binary_search([], 1) == -1
    assert binary_search([7], 7) == 0
    assert binary_search([1, 3], 1) == 0
    assert binary_search([1, 3], 3) == 1
    assert binary_search([1, 3], 2) == -1


# One case per bug. The same cases pass against binary_search above.


def test_catches_the_search_that_misses_the_last_one():
    assert binary_search([1, 3], 3) == 1
    assert bug_misses_the_last_one([1, 3], 3) == -1  # wrong, and silent


def test_catches_the_search_that_never_finishes():
    assert binary_search([1, 3], 0) == -1
    with pytest.raises(RuntimeError):
        bug_never_finishes([1, 3], 0)


def test_catches_the_search_that_reads_past_the_end():
    assert binary_search([1, 3], 9) == -1
    with pytest.raises(IndexError):
        bug_reads_past_the_end([1, 3], 9)
