"""The recursive functions agree with the closed forms and with each other."""

import math

import pytest

from recursion import count_calls, deepest_recursion, factorial, fib, fib_iter, fib_memo


@pytest.mark.parametrize("n", range(0, 12))
def test_factorial_matches_math(n):
    assert factorial(n) == math.factorial(n)


@pytest.mark.parametrize("n", range(0, 25))
def test_three_fibonaccis_agree(n):
    assert fib(n) == fib_memo(n) == fib_iter(n)


def test_the_naive_call_count_follows_the_formula():
    # calls(n) = 2·fib(n+1) − 1: every call except the root is one of two children
    for n in range(0, 20):
        assert count_calls(n) == 2 * fib_iter(n + 1) - 1


def test_memoisation_makes_big_n_instant():
    fib_memo.cache_clear()
    assert fib_memo(300) == fib_iter(300)


def test_python_stops_a_runaway_recursion():
    assert 500 < deepest_recursion() < 2000
