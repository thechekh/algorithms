"""Each demonstration does what the article says, and every copy is exactly as deep as claimed."""

import sys

import pytest

from references_and_copies import (COPIERS, arguments, copies, deep_size, default_argument, hidden, lifetimes,
                                   refcounts, rows_trap, tuple_holding_a_list, two_names)


def test_two_names_share_one_list():
    r = two_names()
    assert r["a"] == r["b"] == [1, 2, 3, 4] and r["c"] == [1, 2, 3, 4, 5]
    assert r["a is b"] and not r["a is c"] and r["a[0] is c[0]"]


def test_the_rows_trap():
    r = rows_trap()
    assert r["shared"] == [[1, 0, 0]] * 3 and r["rows in shared"] == 1
    assert r["separate"] == [[1, 0, 0], [0, 0, 0], [0, 0, 0]] and r["rows in separate"] == 3


def test_the_default_list_is_shared_and_the_fix_is_not():
    r = default_argument()
    assert r["append_to"] == [[1], [1, 2], [1, 2, 3]]
    assert r["append_to_fixed"] == [[1], [2], [3]]


def test_mutating_an_argument_shows_and_rebinding_does_not():
    assert arguments() == {"after add_item": ["old", "new"], "after replace_items": ["old", "new"]}


def test_a_tuple_holding_a_list_changes_and_cannot_be_hashed():
    r = tuple_holding_a_list()
    assert r["pair"] == "([1, 2, 3], 'label')" and "unhashable" in r["hash(pair)"]


def test_shallow_and_deep_copies():
    r = copies()
    assert r["shallow"] == [[1, 2, 99], [3, 4]] and r["shallow shares rows"]
    assert r["deep"] == [[1, 2], [3, 4]] and not r["deep shares rows"]


@pytest.mark.parametrize("name", list(COPIERS))
def test_each_copier_copies_as_deep_as_it_says(name):
    grid = [[10 * i + j for j in range(3)] for i in range(4)]
    copied = COPIERS[name](grid)
    assert copied == grid and copied is not grid
    copied[0].append("changed")
    assert (grid[0][-1] == "changed") == (name == "list(grid)")  # only the outer copy shares rows


def test_deep_size_counts_shared_objects_once_and_survives_cycles():
    assert deep_size([]) == sys.getsizeof([])
    item = [0] * 100
    both = [item, item]
    assert deep_size(both) == sys.getsizeof(both) + deep_size(item)
    loop = []
    loop.append(loop)
    assert deep_size(loop) == sys.getsizeof(loop)
    assert deep_size({"k": "v"}) == sys.getsizeof({"k": "v"}) + sys.getsizeof("k") + sys.getsizeof("v")


def test_reference_counts_rise_and_fall_with_each_name():
    assert [count for _, count in refcounts()] == [2, 3, 4, 3, 2]


def test_small_ints_are_shared_and_none_is_immortal():
    h = hidden()
    assert h["int('256') is int('256')"] and not h["int('257') is int('257')"] and h["int('257') == int('257')"]
    assert h["sys.getrefcount(None)"] > 10**9


def test_a_cycle_waits_for_the_collector():
    r = lifetimes()
    assert r["after del, no cycle"] == ["single freed"]
    assert r["after del, cycle"] == ["single freed"]
    assert r["after gc.collect()"] == ["single freed", "cycle freed"]
    assert r["gc.collect() returned"] >= 2
