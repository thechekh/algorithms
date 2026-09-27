"""The three versions of each problem agree with each other and with brute force."""

import itertools
import math
import random

import pytest

from dynamic_programming import (COINS, apply_edits, calls, coins_greedy, coins_memoised, coins_recursive,
                                 coins_table, coins_used, edit_memoised, edit_recursive, edit_table, edits)


def brute_force_coins(amount: int, coins) -> float:
    """Try every multiset of up to `amount` coins: exhaustive and obviously right."""
    for n in range(amount + 1):
        for combo in itertools.combinations_with_replacement(coins, n):
            if sum(combo) == amount:
                return n
    return math.inf


@pytest.mark.parametrize("coins", [(1, 3, 4), (1, 5, 10, 25), (2, 5), (3, 7), (1, 15, 25)])
def test_coin_change_three_ways_and_brute_force(coins):
    best, last = coins_table(30, coins)
    for amount in range(0, 31):
        expected = brute_force_coins(amount, coins) if amount <= 18 else best[amount]
        assert coins_recursive(amount, coins) == coins_memoised(amount, coins) == best[amount] == expected
        if best[amount] < math.inf:
            used = coins_used(last, amount)
            assert sum(used) == amount and len(used) == best[amount]


def test_greedy_fails_where_the_article_says():
    assert coins_greedy(6, COINS) == [4, 1, 1] and coins_table(6)[0][6] == 2
    assert coins_greedy(30, (1, 15, 25)) == [25, 1, 1, 1, 1, 1] and coins_table(30, (1, 15, 25))[0][30] == 2
    us = (1, 5, 10, 25)
    best, _ = coins_table(100, us)
    assert all(len(coins_greedy(a, us)) == best[a] for a in range(101))  # US coins: greedy is fine


@pytest.mark.parametrize("a, b, d", [("kitten", "sitting", 3), ("flaw", "lawn", 2), ("", "abc", 3),
                                     ("same", "same", 0), ("abc", "", 3), ("sunday", "saturday", 3)])
def test_known_distances(a, b, d):
    assert edit_recursive(a, b) == edit_memoised(a, b) == edit_table(a, b)[-1][-1] == d


@pytest.mark.parametrize("seed", range(30))
def test_edit_distance_three_ways_and_the_edits_it_reads_back(seed):
    rng = random.Random(seed)
    a = "".join(rng.choice("abc") for _ in range(rng.randint(0, 7)))
    b = "".join(rng.choice("abc") for _ in range(rng.randint(0, 7)))
    table = edit_table(a, b)
    assert edit_recursive(a, b) == edit_memoised(a, b) == table[-1][-1] == edit_table(b, a)[-1][-1]
    ops = edits(a, b, table)
    assert apply_edits(ops) == b
    assert sum(op != "keep" for op, *_ in ops) == table[-1][-1]


def test_the_cache_bounds_the_calls():
    calls.clear()
    edit_memoised("abcdefgh", "hgfedcba")
    coins_memoised(40, COINS)
    coins_recursive(10, COINS)
    assert calls["edit_memoised"] <= 9 * 9
    assert calls["coins_memoised"] == 41
    assert calls["coins_recursive"] == 168  # the count the article quotes for amount 10
