"""The linked list behaves like a Python list under random operations."""

import random

import pytest

from arrays_and_lists import LinkedList, growth, list_capacity, operations


@pytest.mark.parametrize("seed", range(20))
def test_linked_list_matches_a_python_list(seed):
    rng = random.Random(seed)
    ours, theirs = LinkedList(), []
    for _ in range(300):
        op = rng.random()
        if op < 0.3:
            v = rng.randint(0, 99)
            ours.push_front(v)
            theirs.insert(0, v)
        elif op < 0.6:
            v = rng.randint(0, 99)
            ours.append(v)
            theirs.append(v)
        elif op < 0.75 and theirs:
            assert ours.pop_front() == theirs.pop(0)
        elif op < 0.9 and len(theirs) >= 1:
            i = rng.randrange(len(theirs))
            v = rng.randint(0, 99)
            ours.insert_after(ours.node_at(i), v)
            theirs.insert(i + 1, v)
        elif len(theirs) >= 2:
            i = rng.randrange(len(theirs) - 1)
            assert ours.remove_after(ours.node_at(i)) == theirs.pop(i + 1)
        assert list(ours) == theirs and len(ours) == len(theirs)
        if theirs:
            assert ours.tail.value == theirs[-1]


def test_timed_operations_leave_the_structures_unchanged():
    ops = operations(50)
    ops.pop("_already_at_middle")
    for impls in ops.values():
        for fn in impls.values():
            fn()
    fresh = operations(50)
    fresh.pop("_already_at_middle")
    assert ops["sum every item"]["list"]() == fresh["sum every item"]["list"]() == sum(range(50))
    assert ops["sum every item"]["linked list"]() == sum(range(50))


def test_list_capacity_never_falls_behind_and_grows_gently():
    steps = growth(500)
    assert all(cap >= n for n, cap in steps)
    capacities = sorted({c for _, c in steps})
    assert all(b / a < 1.6 for a, b in zip(capacities[3:], capacities[4:]))
    assert list_capacity([]) == 0
