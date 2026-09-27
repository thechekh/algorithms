"""Dynamic programming: from recursion to a table.

Article: https://chekh.dev/writing/dynamic-programming-from-recursion-to-a-table/
Run:     uv run python dynamic_programming.py                (about five minutes: the plain
                                                             recursions are the slow part)
         uv run python dynamic_programming.py --charts-only  (redraw from results/)
         uv run pytest tests/test_dynamic_programming.py

Two classic problems, each solved three ways: a plain recursion, the same recursion
with a cache, and a table filled from the bottom up. Coin change: the fewest coins
that make an amount. Edit distance: the fewest single-letter edits that turn one word
into another. Calls are counted and times measured as the input grows.
"""

import functools
import json
import math
import random
import sys
import time
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt

from _common import ACCENT, INK, INK_2, MUTED, machine, plain_numbers, save, seconds

SLUG = "dynamic-programming-from-recursion-to-a-table"
COINS = (1, 3, 4)
calls = Counter()  # how many times each function body ran, for the charts


# --- Coin change -------------------------------------------------------------------------


def coins_greedy(amount: int, coins=COINS) -> list[int] | None:
    """Take the largest coin that fits, again and again. Fast, and sometimes wrong."""
    taken = []
    for coin in sorted(coins, reverse=True):
        while amount >= coin:
            amount -= coin
            taken.append(coin)
    return taken if amount == 0 else None


def coins_recursive(amount: int, coins=COINS) -> float:
    """Fewest coins for `amount`: try each coin as the last one, then recurse."""
    calls["coins_recursive"] += 1
    if amount == 0:
        return 0
    best = math.inf
    for coin in coins:
        if coin <= amount:
            best = min(best, 1 + coins_recursive(amount - coin, coins))
    return best


def coins_memoised(amount: int, coins=COINS) -> float:
    """The same recursion, remembering each amount's answer the first time."""

    @functools.cache
    def fewest(a: int) -> float:
        calls["coins_memoised"] += 1
        if a == 0:
            return 0
        options = [1 + fewest(a - c) for c in coins if c <= a]
        return min(options, default=math.inf)

    return fewest(amount)


def coins_table(amount: int, coins=COINS) -> tuple[list, list]:
    """Bottom-up: fill best[a] from a = 0 up, each from cells to its left."""
    best = [0] + [math.inf] * amount
    last = [None] * (amount + 1)  # the coin that achieves best[a]
    for a in range(1, amount + 1):
        for coin in coins:
            if coin <= a and best[a - coin] + 1 < best[a]:
                best[a], last[a] = best[a - coin] + 1, coin
    return best, last


def coins_used(last: list, amount: int) -> list[int]:
    """Walk the table back from `amount` to 0 to read off the coins."""
    used = []
    while amount > 0:
        used.append(last[amount])
        amount -= last[amount]
    return used


# --- Edit distance -----------------------------------------------------------------------


def edit_recursive(a: str, b: str) -> int:
    """Distance between a and b, by trying all three edits on the last letter."""

    def d(i: int, j: int) -> int:  # distance between a[:i] and b[:j]
        calls["edit_recursive"] += 1
        if i == 0 or j == 0:
            return i + j  # insert or delete everything that is left
        return min(d(i - 1, j) + 1,  # delete a[i-1]
                   d(i, j - 1) + 1,  # insert b[j-1]
                   d(i - 1, j - 1) + (a[i - 1] != b[j - 1]))  # keep or substitute

    return d(len(a), len(b))


def edit_memoised(a: str, b: str) -> int:
    """The same recursion with a cache: each (i, j) is worked out once."""

    @functools.cache
    def d(i: int, j: int) -> int:
        calls["edit_memoised"] += 1
        if i == 0 or j == 0:
            return i + j
        return min(d(i - 1, j) + 1, d(i, j - 1) + 1,
                   d(i - 1, j - 1) + (a[i - 1] != b[j - 1]))

    return d(len(a), len(b))


def edit_table(a: str, b: str) -> list[list[int]]:
    """table[i][j] is the distance between a[:i] and b[:j], filled row by row."""
    table = [[i + j if i == 0 or j == 0 else 0 for j in range(len(b) + 1)]
             for i in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            table[i][j] = min(table[i - 1][j] + 1,  # delete a letter
                              table[i][j - 1] + 1,  # insert a letter
                              table[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    return table


def edits(a: str, b: str, table: list[list[int]]) -> list[tuple]:
    """Walk back from the bottom-right corner to read off one cheapest list of edits."""
    i, j, ops = len(a), len(b), []
    while i or j:
        if i and j and table[i][j] == table[i - 1][j - 1] + (a[i - 1] != b[j - 1]):
            ops.append(("keep" if a[i - 1] == b[j - 1] else "substitute", a[i - 1], b[j - 1], i, j))
            i, j = i - 1, j - 1
        elif i and table[i][j] == table[i - 1][j] + 1:
            ops.append(("delete", a[i - 1], "", i, j))
            i -= 1
        else:
            ops.append(("insert", "", b[j - 1], i, j))
            j -= 1
    return ops[::-1]


def apply_edits(ops: list[tuple]) -> str:
    return "".join(new for op, old, new, *_ in ops if op != "delete")


# --- Experiments ---------------------------------------------------------------------------


def timed(fn) -> float:
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


def compute() -> dict:
    results: dict = {"machine": machine(), "coins": list(COINS)}

    best, last = coins_table(12)
    results["coin_table"] = {"best": best, "last": last}
    greedy = coins_greedy(6)
    print(f"coins {COINS}, amount 6: greedy {greedy} ({len(greedy)} coins), table {coins_used(last, 6)} ({best[6]} coins)")
    wrong = [a for a in range(1, 101) if len(coins_greedy(a)) > coins_table(a)[0][a]]
    results["greedy_wrong"] = {"coins": list(COINS), "amounts": wrong}
    print(f"greedy is wrong for {len(wrong)} of the amounts 1..100 with coins {COINS}: {wrong[:8]}...")
    us = (1, 5, 10, 25)
    results["greedy_wrong_us"] = [a for a in range(1, 101) if len(coins_greedy(a, us)) > coins_table(a, us)[0][a]]

    c = results["coin_calls"] = {"amounts": [], "recursive": [], "memoised": [], "recursive_seconds": [], "memoised_seconds": [], "table_seconds": []}
    for amount in range(5, 41, 5):
        calls.clear()
        t_rec = timed(lambda: coins_recursive(amount))
        t_memo = timed(lambda: coins_memoised(amount))
        t_table = timed(lambda: coins_table(amount))
        for key, value in [("amounts", amount), ("recursive", calls["coins_recursive"]), ("memoised", calls["coins_memoised"]),
                           ("recursive_seconds", t_rec), ("memoised_seconds", t_memo), ("table_seconds", t_table)]:
            c[key].append(value)
        print(f"coin change, amount {amount:3d}: recursive {c['recursive'][-1]:>12,} calls {seconds(t_rec):>7}"
              f"   memoised {c['memoised'][-1]:4d} calls {seconds(t_memo):>7}   table {seconds(t_table):>7}")

    table = edit_table("kitten", "sitting")
    ops = edits("kitten", "sitting", table)
    results["edit_example"] = {"a": "kitten", "b": "sitting", "table": table, "ops": ops}
    print("kitten -> sitting:", table[-1][-1], "edits:", [(op, old, new) for op, old, new, *_ in ops if op != "keep"])

    rng = random.Random(0)
    e = results["edit_calls"] = {"lengths": [], "recursive": [], "memoised": [], "cells": [], "recursive_seconds": [], "memoised_seconds": [], "table_seconds": []}
    for n in range(2, 13):
        a = "".join(rng.choice("acgt") for _ in range(n))
        b = "".join(rng.choice("acgt") for _ in range(n))
        calls.clear()
        t_rec = timed(lambda: edit_recursive(a, b))
        t_memo = timed(lambda: edit_memoised(a, b))
        t_table = timed(lambda: edit_table(a, b))
        for key, value in [("lengths", n), ("recursive", calls["edit_recursive"]), ("memoised", calls["edit_memoised"]),
                           ("cells", (n + 1) ** 2), ("recursive_seconds", t_rec), ("memoised_seconds", t_memo), ("table_seconds", t_table)]:
            e[key].append(value)
        print(f"edit distance, length {n:2d}: recursive {e['recursive'][-1]:>12,} calls {seconds(t_rec):>7}"
              f"   memoised {e['memoised'][-1]:4d} calls   table {(n + 1) ** 2:4d} cells {seconds(t_table):>7}")

    results["edit_long"] = {"lengths": [], "seconds": []}
    for n in (100, 300, 1000, 3000):
        a = "".join(rng.choice("acgt") for _ in range(n))
        b = "".join(rng.choice("acgt") for _ in range(n))
        t = timed(lambda: edit_table(a, b))
        results["edit_long"]["lengths"].append(n)
        results["edit_long"]["seconds"].append(t)
        print(f"edit distance by table, two strings of {n:5d}: {seconds(t)}")
    return results


# --- Charts --------------------------------------------------------------------------------


def draw_edit_table(results: dict) -> None:
    ex = results["edit_example"]
    a, b, table = ex["a"], ex["b"], ex["table"]
    on_path = {(i, j) for *_, i, j in ex["ops"]} | {(0, 0)}
    fig, ax = plt.subplots(figsize=(6.8, 5.0))
    rows, cols = len(a) + 1, len(b) + 1
    ax.set_xlim(-1.2, cols + 0.1)
    ax.set_ylim(-rows - 1.9, 1.3)
    ax.axis("off")
    for j, ch in enumerate(" " + b):
        ax.text(j + 0.5, 0.45, ch if j else "", ha="center", va="center", fontsize=11, color=INK, fontweight="semibold")
    for i, ch in enumerate(" " + a):
        ax.text(-0.45, -i - 0.5, ch if i else "", ha="center", va="center", fontsize=11, color=INK, fontweight="semibold")
    for i in range(rows):
        for j in range(cols):
            lit = (i, j) in on_path
            ax.add_patch(plt.Rectangle((j, -i - 1), 1, 1, facecolor=ACCENT if lit else "#faf9f6", edgecolor=MUTED, linewidth=0.8))
            ax.text(j + 0.5, -i - 0.5, str(table[i][j]), ha="center", va="center", fontsize=10, color="white" if lit else INK)
    changes = [f"{op} {old or ''}{' to ' if op == 'substitute' else ''}{new if op != 'delete' else ''}".replace("  ", " ")
               for op, old, new, *_ in ex["ops"] if op != "keep"]
    ax.text(-1.1, -rows - 0.45, f"cell (i, j): edits to turn the first i letters of \"{a}\" into the first j of \"{b}\"",
            fontsize=8.5, color=INK_2, va="top")
    ax.text(-1.1, -rows - 1.05, f"bottom-right: {table[-1][-1]} edits; the green path reads them back: " + ", ".join(changes),
            fontsize=8.5, color=INK, va="top")
    save(fig, SLUG, "edit-table")


def draw_coin_table(results: dict) -> None:
    best, last = results["coin_table"]["best"], results["coin_table"]["last"]
    n = len(best)
    fig, ax = plt.subplots(figsize=(7.8, 3.3))
    ax.set_xlim(-1.6, n + 0.1)
    ax.set_ylim(-3.9, 1.6)
    ax.axis("off")
    chain, a = [], 6
    while a > 0:
        chain.append(a)
        a -= last[a]
    chain.append(0)
    for row, label, values in [(0, "amount", list(range(n))), (1, "fewest coins", best), (2, "last coin", last)]:
        ax.text(-0.15, -row - 0.5, label, ha="right", va="center", fontsize=8.5, color=INK_2)
        for a, v in enumerate(values):
            lit = a in chain and row in (0, 1)
            ax.add_patch(plt.Rectangle((a, -row - 1), 1, 1, facecolor=ACCENT if lit else ("#eceee6" if row == 0 else "#faf9f6"), edgecolor=MUTED, linewidth=0.8))
            ax.text(a + 0.5, -row - 0.5, "-" if v is None else str(v), ha="center", va="center", fontsize=9.5, color="white" if lit else INK)
    for x1, x2 in zip(chain, chain[1:]):
        ax.annotate("", (x2 + 0.5, 0.05), (x1 + 0.5, 0.05), arrowprops={"arrowstyle": "-|>", "color": ACCENT, "connectionstyle": "arc3,rad=0.45", "linewidth": 1.1})
        ax.text((x1 + x2) / 2 + 0.5, 0.75, f"take a {x1 - x2}", ha="center", va="bottom", fontsize=8, color=ACCENT)
    ax.text(0, -3.35, f"coins {results['coins']}: best[a] = 1 + the smallest of best[a - coin]. For 6 the table says 2 coins (3 + 3);"
            f" taking the largest coin first gives 4 + 1 + 1.", fontsize=8.3, color=INK, va="top")
    save(fig, SLUG, "coin-table")


def draw_calls(results: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.3), sharey=True)
    c, e = results["coin_calls"], results["edit_calls"]
    for ax, xs, rec, memo, title, xlabel in [
        (axes[0], c["amounts"], c["recursive"], c["memoised"], f"coin change, coins {tuple(results['coins'])}", "amount"),
        (axes[1], e["lengths"], e["recursive"], e["memoised"], "edit distance, two random strings", "length of each string"),
    ]:
        ax.plot(xs, rec, color=INK_2, linewidth=1.8, marker="o", markersize=3.5, markeredgecolor="white", markeredgewidth=0.8)
        ax.plot(xs, memo, color=ACCENT, linewidth=2, marker="o", markersize=3.5, markeredgecolor="white", markeredgewidth=0.8)
        ax.annotate(f"plain recursion: {rec[-1]:,}", (xs[-1], rec[-1]), xytext=(-4, 4), textcoords="offset points", ha="right", va="bottom", fontsize=8, color=INK_2)
        ax.annotate(f"with a cache: {memo[-1]:,}", (xs[-1], memo[-1]), xytext=(-4, 6), textcoords="offset points", ha="right", fontsize=8, color=ACCENT)
        ax.set_yscale("log")
        plain_numbers(ax.yaxis)
        ax.set_title(title, fontsize=9.5)
        ax.set_xlabel(xlabel)
    axes[0].set_ylabel("calls (log scale)")
    fig.suptitle("The same recursion, with and without remembering answers", fontsize=10.5)
    fig.tight_layout()
    save(fig, SLUG, "calls")


if __name__ == "__main__":
    path = Path(__file__).parent / "results" / f"{SLUG}.json"
    if "--charts-only" in sys.argv:
        results = json.loads(path.read_text())
    else:
        results = compute()
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(results, indent=1))
        print(f"  wrote {path.name}")
    draw_edit_table(results)
    draw_coin_table(results)
    draw_calls(results)
