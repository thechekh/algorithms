"""The hash table behaves like a dict, whatever the hash function, and grows when full."""

import random

import pytest

from hash_table import HashMap, simple_hash


@pytest.mark.parametrize("hash_function", [hash, simple_hash, len, lambda key: 1])
@pytest.mark.parametrize("seed", range(20))
def test_matches_a_dict_under_random_operations(hash_function, seed):
    rng = random.Random(seed)
    ours, theirs = HashMap(hash_function=hash_function), {}
    for _ in range(300):
        key = f"k{rng.randint(0, 40)}"
        op = rng.random()
        if op < 0.6:
            value = rng.randint(0, 1000)
            ours.put(key, value)
            theirs[key] = value
        elif op < 0.8:
            assert ours.delete(key) == (theirs.pop(key, None) is not None)
        else:
            assert ours.get(key) == theirs.get(key)
            assert (key in ours) == (key in theirs)
    assert len(ours) == len(theirs)
    for key, value in theirs.items():
        assert ours.get(key) == value


def test_it_grows_and_keeps_every_entry():
    table = HashMap(capacity=8)
    for i in range(1000):
        table.put(f"key{i}", i)
    assert len(table.buckets) >= 1000 / 0.75
    assert table.load_factor <= 0.75
    assert all(table.get(f"key{i}") == i for i in range(1000))


def test_without_growth_the_chains_get_long():
    table = HashMap(capacity=8, resize=False)
    for i in range(1000):
        table.put(f"key{i}", i)
    assert len(table.buckets) == 8 and table.longest_chain() >= 100


def test_a_constant_hash_puts_everything_in_one_bucket():
    table = HashMap(hash_function=lambda key: 1)
    for i in range(50):
        table.put(f"key{i}", i)
    assert sum(1 for b in table.buckets if b) == 1


def test_the_simple_hash_is_deterministic_and_spreads():
    assert simple_hash("ada") == simple_hash("ada")
    assert len({simple_hash(f"key{i}") % 64 for i in range(200)}) > 40
