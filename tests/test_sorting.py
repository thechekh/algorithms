"""Every algorithm agrees with sorted() on awkward inputs, and the stable ones keep
equal elements in their original order."""

import random

import pytest

from sorting import bubble_sort, insertion_sort, merge_sort, quick_sort

ALGORITHMS = [bubble_sort, insertion_sort, merge_sort, quick_sort]
AWKWARD = [[], [1], [2, 1], [1, 1, 1], [3, 1, 2, 1, 3], list(range(20)), list(range(20, 0, -1)), [5, -2, 9, -2, 0]]


@pytest.mark.parametrize("algorithm", ALGORITHMS)
@pytest.mark.parametrize("items", AWKWARD)
def test_awkward_inputs(algorithm, items):
    assert algorithm(items) == sorted(items)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
@pytest.mark.parametrize("seed", range(50))
def test_random_inputs(algorithm, seed):
    rng = random.Random(seed)
    items = [rng.randint(-30, 30) for _ in range(rng.randint(0, 200))]
    assert algorithm(items) == sorted(items)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_does_not_change_the_input(algorithm):
    items = [3, 1, 2]
    algorithm(items)
    assert items == [3, 1, 2]


class Record:
    """Compares by key only, so two records with the same key are 'equal' to the sort."""

    def __init__(self, key, tag):
        self.key, self.tag = key, tag

    def __lt__(self, other):
        return self.key < other.key

    def __le__(self, other):
        return self.key <= other.key

    def __gt__(self, other):
        return self.key > other.key

    def __eq__(self, other):
        return self.key == other.key


@pytest.mark.parametrize("algorithm", [bubble_sort, insertion_sort, merge_sort])
def test_stable_sorts_keep_the_original_order_of_equal_keys(algorithm):
    records = [Record(k, tag) for k, tag in [(2, "a"), (1, "b"), (2, "c"), (1, "d"), (2, "e")]]
    assert [r.tag for r in algorithm(records)] == ["b", "d", "a", "c", "e"]
