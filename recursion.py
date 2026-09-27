"""Recursion, drawn.

Article: https://chekh.dev/writing/recursion-drawn/
Run:     uv run python recursion.py                 (about ten seconds)
         uv run python recursion.py --charts-only   (redraw from results/)
         uv run pytest tests/test_recursion.py

The call stack for factorial(4), the call tree for fib(5), how many calls the naive
Fibonacci makes as n grows against the memoised version, and how deep Python lets a
recursion go.
"""

import functools
import json
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
from _common import ACCENT, INK, INK_2, MUTED, plain_numbers, save

SLUG = "recursion-drawn"


def factorial(n: int) -> int:
    """n! = n * (n - 1)!, and 0! = 1. The base case is what stops it."""
    if n <= 1:
        return 1
    return n * factorial(n - 1)


def fib(n: int) -> int:
    """The naive Fibonacci: two calls per call, most of them repeats."""
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)


@functools.cache
def fib_memo(n: int) -> int:
    """The same function, remembering every answer: each n is computed once."""
    if n < 2:
        return n
    return fib_memo(n - 1) + fib_memo(n - 2)


def fib_iter(n: int) -> int:
    """No recursion at all: walk up from the bottom."""
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def count_calls(n: int) -> int:
    """How many times the naive fib is called to compute fib(n)."""
    calls = 0

    def counted(k: int) -> int:
        nonlocal calls
        calls += 1
        if k < 2:
            return k
        return counted(k - 1) + counted(k - 2)

    counted(n)
    return calls


def deepest_recursion() -> int:
    """How many nested calls Python allows before RecursionError."""

    def down(depth: int) -> int:
        try:
            return down(depth + 1)
        except RecursionError:
            return depth

    return down(1)


def compute() -> dict:
    results: dict = {"calls": {}, "timings": {}}
    for n in range(0, 31, 5):
        results["calls"][str(n)] = {"naive": count_calls(n), "memoised": n + 1}
    for n in (20, 25, 30, 32):
        start = time.perf_counter()
        fib(n)
        naive = time.perf_counter() - start
        fib_memo.cache_clear()
        start = time.perf_counter()
        fib_memo(n)
        memo = time.perf_counter() - start
        results["timings"][n] = {"naive": naive, "memoised": memo, "calls": count_calls(n)}
        print(f"fib({n}): naive {naive:7.3f} s and {results['timings'][n]['calls']:>10,} calls   memoised {memo * 1e6:6.0f} us")
    results["recursion_limit"] = sys.getrecursionlimit()
    results["deepest"] = deepest_recursion()
    print(f"recursion limit {results['recursion_limit']}; the deepest call that ran: {results['deepest']}")
    return results


def draw_stack() -> None:
    """factorial(4): the stack grows to four frames, then unwinds with a value each step."""
    steps = [
        ([4], None), ([4, 3], None), ([4, 3, 2], None), ([4, 3, 2, 1], None),
        ([4, 3, 2, 1], 1), ([4, 3, 2], 2), ([4, 3], 6), ([4], 24), ([], 24),
    ]
    fig, ax = plt.subplots(figsize=(8.2, 3.4))
    ax.set_xlim(-0.4, len(steps) * 0.95)
    ax.set_ylim(-1.0, 4.6)
    ax.axis("off")
    for s, (frames, value) in enumerate(steps):
        x = s * 0.95
        ax.plot([x, x + 0.7], [0, 0], color=MUTED, linewidth=1)
        for depth, n in enumerate(frames):
            top = depth == len(frames) - 1
            ax.add_patch(plt.Rectangle((x, depth * 0.85), 0.7, 0.7, facecolor="#faf9f6", edgecolor=ACCENT if top and value is not None and s >= 4 else MUTED, linewidth=1.2 if top else 1))
            ax.text(x + 0.35, depth * 0.85 + 0.35, f"factorial({n})", ha="center", va="center", fontsize=7.5, color=INK)
        if value is not None:
            ax.text(x + 0.35, len(frames) * 0.85 + 0.15, f"returns {value}", ha="center", va="bottom", fontsize=8, color=ACCENT)
        elif len(frames) == 4:
            ax.text(x + 0.35, len(frames) * 0.85 + 0.15, "base case", ha="center", va="bottom", fontsize=8, color=INK_2)
        ax.text(x + 0.35, -0.35, f"step {s + 1}", ha="center", va="top", fontsize=8, color=INK_2)
    ax.text(0, 4.45, "calls pile up until the base case, then each one returns to the one below it", fontsize=9.5, color=INK, va="top")
    save(fig, SLUG, "call-stack")


def draw_tree() -> None:
    """The call tree for fib(5): every node is a call, and most of them are repeats."""
    nodes, edges = [], []

    def build(n: int, depth: int) -> int:
        index = len(nodes)
        nodes.append([n, depth, 0.0])
        if n >= 2:
            for child in (n - 1, n - 2):
                edges.append((index, build(child, depth + 1)))
        return index

    build(5, 0)
    # Leaves left to right; every other node above the middle of its children.
    next_x = 0.0

    def place(index: int) -> float:
        nonlocal next_x
        children = [b for a, b in edges if a == index]
        if not children:
            nodes[index][2] = next_x
            next_x += 1.0
        else:
            nodes[index][2] = sum(place(c) for c in children) / len(children)
        return nodes[index][2]

    place(0)
    counts = {}
    for n, _, _ in nodes:
        counts[n] = counts.get(n, 0) + 1
    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    ax.set_xlim(-0.6, next_x - 0.4)
    ax.set_ylim(-4.6, 0.6)
    ax.axis("off")
    for a, b in edges:
        ax.plot([nodes[a][2], nodes[b][2]], [-nodes[a][1], -nodes[b][1]], color=MUTED, linewidth=1, zorder=1)
    for n, depth, x in nodes:
        ax.add_patch(plt.Circle((x, -depth), 0.3, facecolor=ACCENT if n == 2 else ("#faf9f6" if n >= 2 else "#e4e4da"), edgecolor=ACCENT if n == 2 else MUTED, linewidth=1, zorder=2))
        ax.text(x, -depth, f"fib({n})", ha="center", va="center", fontsize=7, color="white" if n == 2 else INK, zorder=3)
    summary = ", ".join(f"fib({n}) × {counts[n]}" for n in sorted(counts, reverse=True))
    ax.text(-0.5, 0.55, f"{len(nodes)} calls to compute fib(5) = 5: {summary}", fontsize=9.5, color=INK, va="top")
    save(fig, SLUG, "call-tree")


def draw_calls(results: dict) -> None:
    ns = sorted(int(n) for n in results["calls"])
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    naive = [results["calls"][str(n)]["naive"] for n in ns]
    memo = [results["calls"][str(n)]["memoised"] for n in ns]
    ax.plot(ns, naive, color=INK_2, linewidth=1.8, marker="o", markersize=4, markeredgecolor="white", markeredgewidth=0.8)
    ax.plot(ns, memo, color=ACCENT, linewidth=2, marker="o", markersize=4, markeredgecolor="white", markeredgewidth=0.8)
    ax.annotate(f"naive: {naive[-1]:,} calls", (ns[-1], naive[-1]), xytext=(-8, 0), textcoords="offset points", ha="right", va="center", fontsize=8.5, color=INK_2)
    ax.annotate(f"memoised: {memo[-1]} calls", (ns[-1], memo[-1]), xytext=(-8, 6), textcoords="offset points", ha="right", fontsize=8.5, color=ACCENT)
    ax.set_yscale("log")
    plain_numbers(ax.yaxis)
    ax.set_xticks(ns)
    ax.set_xlabel("n")
    ax.set_ylabel("calls to compute fib(n) (log scale)")
    ax.set_title("Remembering answers turns an exponential into a straight line")
    save(fig, SLUG, "calls")


if __name__ == "__main__":
    path = Path(__file__).parent / "results" / f"{SLUG}.json"
    if "--charts-only" in sys.argv:
        results = json.loads(path.read_text())
    else:
        results = compute()
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(results, indent=2))
        print(f"  wrote {path.name}")
    draw_stack()
    draw_tree()
    draw_calls(results)
