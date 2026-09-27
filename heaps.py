"""Heaps and priority queues: the array trick behind heapq.

Article: https://chekh.dev/writing/heaps-and-priority-queues-the-array-trick-behind-heapq/
Run:     uv run python heaps.py                 (about a minute)
         uv run python heaps.py --charts-only   (redraw from results/)
         uv run pytest tests/test_heaps.py

A binary min-heap in plain Python on a list, traced as it pushes and pops, its
comparisons counted when it is built item by item and in one pass, and four ways of
finding the ten largest of a million numbers.
"""

import heapq
import json
import random
import sys
from pathlib import Path

import matplotlib.pyplot as plt

from _common import ACCENT, INK, INK_2, MUTED, machine, plain_numbers, save, seconds, time_axis, time_per_call

SLUG = "heaps-and-priority-queues-the-array-trick-behind-heapq"


class Heap:
    """A binary min-heap on a Python list: the smallest item is always at index 0.

    The children of the item at index i sit at 2i + 1 and 2i + 2, its parent at
    (i - 1) // 2, so the tree needs no pointers at all.
    """

    def __init__(self, items=()):
        self.items = list(items)
        for i in reversed(range(len(self.items) // 2)):  # heapify, bottom-up
            self._sift_down(i)

    def push(self, item) -> None:
        self.items.append(item)  # the new item starts as the last leaf
        self._sift_up(len(self.items) - 1)

    def pop(self):
        items = self.items
        last = items.pop()
        if not items:
            return last
        smallest, items[0] = items[0], last  # the last leaf takes the root's place
        self._sift_down(0)
        return smallest

    def peek(self):
        return self.items[0]

    def __len__(self) -> int:
        return len(self.items)

    def _sift_up(self, i: int) -> None:
        while i > 0:
            parent = (i - 1) // 2
            if not self.items[i] < self.items[parent]:
                return
            self._swap(i, parent)
            i = parent

    def _sift_down(self, i: int) -> None:
        items, n = self.items, len(self.items)
        while True:
            smallest, left, right = i, 2 * i + 1, 2 * i + 2
            if left < n and items[left] < items[smallest]:
                smallest = left
            if right < n and items[right] < items[smallest]:
                smallest = right
            if smallest == i:
                return
            self._swap(i, smallest)
            i = smallest

    def _swap(self, i: int, j: int) -> None:
        self.items[i], self.items[j] = self.items[j], self.items[i]


class TracedHeap(Heap):
    """The same heap, recording the list after every swap, for the diagrams."""

    def __init__(self, items=()):
        self.steps: list[tuple[list, int, int]] = []
        super().__init__(items)
        self.steps.clear()

    def _swap(self, i: int, j: int) -> None:
        super()._swap(i, j)
        self.steps.append((list(self.items), i, j))


class Counted:
    """A number that counts every comparison made with it."""

    comparisons = 0
    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value

    def __lt__(self, other) -> bool:
        Counted.comparisons += 1
        return self.value < other.value


# --- Four ways to find the k largest ---------------------------------------------------


def top_k_sorted(data, k: int) -> list:
    """Sort everything, keep the end: O(n log n) time, a full copy in memory."""
    return sorted(data, reverse=True)[:k]


def top_k_full_heap(data, k: int) -> list:
    """Heapify everything (negated, since heapq is a min-heap), pop k: O(n + k log n)."""
    heap = [-x for x in data]
    heapq.heapify(heap)
    return [-heapq.heappop(heap) for _ in range(k)]


def top_k_heap(data, k: int) -> list:
    """One pass, k items of memory: keep the k largest so far in a min-heap."""
    heap = Heap()
    for x in data:
        if len(heap) < k:
            heap.push(x)
        elif x > heap.peek():  # bigger than the smallest of the k kept so far
            heap.pop()
            heap.push(x)
    return sorted(heap.items, reverse=True)


def top_k_heapq(data, k: int) -> list:
    """The standard library's version of the same idea."""
    return heapq.nlargest(k, data)


TOP_K = {"sort everything": top_k_sorted, "heapify everything": top_k_full_heap,
         "heap of 10, in Python": top_k_heap, "heapq.nlargest": top_k_heapq}
SIZES = [1_000, 3_000, 10_000, 30_000, 100_000, 300_000, 1_000_000]
BUILD_SIZES = [1_000, 3_000, 10_000, 30_000, 100_000]


def build_comparisons(values: list) -> dict[str, float]:
    """Comparisons per item to build a heap by pushing one at a time, and in one pass."""
    Counted.comparisons = 0
    heap = Heap()
    for v in values:
        heap.push(Counted(v))
    pushes = Counted.comparisons / len(values)
    Counted.comparisons = 0
    Heap(Counted(v) for v in values)
    return {"push one by one": pushes, "heapify in one pass": Counted.comparisons / len(values)}


def compute() -> dict:
    rng = random.Random(0)
    results: dict = {"machine": machine(), "sizes": SIZES, "build_sizes": BUILD_SIZES, "top_k": {}, "build": {}}

    for order in ("random", "descending"):
        results["build"][order] = {"push one by one": [], "heapify in one pass": []}
        for n in BUILD_SIZES:
            values = [rng.random() for _ in range(n)]
            if order == "descending":
                values.sort(reverse=True)  # the worst case for a min-heap
            for method, per_item in build_comparisons(values).items():
                results["build"][order][method].append(per_item)
        print(f"build, {order:10s} " + "   ".join(f"{m}: " + " ".join(f"{v:.2f}" for v in vals) for m, vals in results["build"][order].items()))

    for name, fn in TOP_K.items():
        results["top_k"][name] = []
        for n in SIZES:
            data = [rng.random() for _ in range(n)]
            expected = sorted(data, reverse=True)[:10]
            assert fn(data, 10) == expected, name
            results["top_k"][name].append(time_per_call(lambda: fn(data, 10), repeats=3))
        print(f"top 10 by {name:22s} " + "  ".join(f"{seconds(t):>7}" for t in results["top_k"][name]))
    return results


# --- Diagrams ----------------------------------------------------------------------------


def positions(n: int, x0: float, width: float, y0: float, gap: float) -> list[tuple[float, float]]:
    """Where node i of a complete binary tree goes: each level splits its width in two."""
    out = []
    for i in range(n):
        level = (i + 1).bit_length() - 1
        slot = i + 1 - 2 ** level
        out.append((x0 + width * (slot + 0.5) / 2 ** level, y0 - level * gap))
    return out


def draw_tree(ax, items, x0, width, y0, gap, radius, highlight=(), fontsize=9, index=False):
    pos = positions(len(items), x0, width, y0, gap)
    for i in range(1, len(items)):
        (x1, y1), (x2, y2) = pos[(i - 1) // 2], pos[i]
        ax.plot([x1, x2], [y1, y2], color=MUTED, linewidth=1, zorder=1)
    for i, (x, y) in enumerate(pos):
        lit = i in highlight
        ax.add_patch(plt.Circle((x, y), radius, facecolor=ACCENT if lit else "#faf9f6", edgecolor=ACCENT if lit else INK_2, linewidth=1, zorder=2))
        ax.text(x, y, str(items[i]), ha="center", va="center", fontsize=fontsize, color="white" if lit else INK, zorder=3)
        if index:
            ax.text(x, y - radius - 0.05, f"[{i}]", ha="center", va="top", fontsize=7, color=INK_2)


def draw_array_tree() -> None:
    heap = Heap([7, 2, 9, 4, 8, 3, 6, 5])
    heap.push(1)
    items = heap.items
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(-4.0, 1.1)
    ax.axis("off")
    draw_tree(ax, items, 0.5, 9.0, 0.6, 0.75, 0.2, highlight={0}, index=True)
    cell = 0.8
    left = 5 - cell * len(items) / 2
    for i, v in enumerate(items):
        level = (i + 1).bit_length() - 1
        face = ACCENT if i == 0 else ["#faf9f6", "#eceee6", "#dfe5df", "#d2dcd2"][level]
        ax.add_patch(plt.Rectangle((left + i * cell, -3.5), cell, 0.55, facecolor=face, edgecolor=INK_2, linewidth=1))
        ax.text(left + (i + 0.5) * cell, -3.22, str(v), ha="center", va="center", fontsize=9.5, color="white" if i == 0 else INK)
        ax.text(left + (i + 0.5) * cell, -3.58, str(i), ha="center", va="top", fontsize=7.5, color=INK_2)
    ax.text(left - 0.15, -3.22, "the list", ha="right", va="center", fontsize=8.5, color=INK_2)
    ax.text(5, -2.6, "children of index i: 2i + 1 and 2i + 2     parent: (i - 1) // 2     levels shaded alike",
            ha="center", va="center", fontsize=8, color=INK_2)
    ax.text(0.5, 1.05, "a heap is a list read as a tree: every parent is smaller than its children", fontsize=9, color=INK, va="top")
    save(fig, SLUG, "tree")


def draw_sift() -> None:
    heap = TracedHeap([7, 2, 9, 4, 8, 3, 6, 5])
    before = list(heap.items)
    heap.push(1)
    push_steps = [(before + [1], {len(before)})] + [(state, {j}) for state, i, j in heap.steps]
    heap.steps.clear()
    full = list(heap.items)
    heap.pop()
    moved = [full[-1]] + full[1:-1]
    pop_steps = [(moved, {0})] + [(state, {j}) for state, i, j in heap.steps]
    rows = [("push 1: append it as the last leaf, then swap it up while it is smaller than its parent", push_steps),
            ("pop: take the root, move the last leaf into its place, then swap it down past the smaller child", pop_steps)]
    fig, axes = plt.subplots(2, 1, figsize=(8.4, 5.4))
    for ax, (title, steps) in zip(axes, rows):
        ax.set_xlim(0, 4 * 2.1)
        ax.set_ylim(-2.55, 0.55)
        ax.axis("off")
        ax.set_title(title, fontsize=8.8, loc="left", color=INK)
        for s, (items, lit) in enumerate(steps):
            draw_tree(ax, items, s * 2.1 + 0.05, 1.95, 0.25, 0.72, 0.11, highlight=lit, fontsize=7.5)
            ax.text(s * 2.1 + 1.03, -2.5, "start" if s == 0 else f"swap {s}", ha="center", va="bottom", fontsize=7.5, color=INK_2)
    fig.tight_layout()
    save(fig, SLUG, "sift")


def draw_top_k(results: dict) -> None:
    fig, ax = plt.subplots(figsize=(6.6, 3.7))
    colors = {"sort everything": INK_2, "heapify everything": MUTED, "heap of 10, in Python": INK, "heapq.nlargest": ACCENT}
    for name, times in results["top_k"].items():
        ax.plot(SIZES, times, color=colors[name], linewidth=2 if name == "heapq.nlargest" else 1.6, marker="o", markersize=3.5, markeredgecolor="white", markeredgewidth=0.8)
        nudge = {"sort everything": 7, "heap of 10, in Python": -6}.get(name, 0)
        ax.annotate(name, (SIZES[-1], times[-1]), xytext=(6, nudge), textcoords="offset points", fontsize=8.5, color=colors[name], va="center")
    ax.set_xscale("log")
    ax.set_yscale("log")
    plain_numbers(ax.xaxis)
    time_axis(ax.yaxis)
    ax.set_xlim(800, 1.3e6)
    ax.set_xlabel("numbers to search (log scale)")
    ax.set_ylabel("time to find the 10 largest (log scale)")
    ax.set_title("The ten largest of n random numbers, four ways")
    fig.subplots_adjust(right=0.72)
    save(fig, SLUG, "top-k")


def draw_build(results: dict) -> None:
    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    styles = {("random", "push one by one"): (INK_2, "--"), ("random", "heapify in one pass"): (MUTED, "--"),
              ("descending", "push one by one"): (INK, "-"), ("descending", "heapify in one pass"): (ACCENT, "-")}
    for (order, method), (color, style) in styles.items():
        values = results["build"][order][method]
        ax.plot(BUILD_SIZES, values, color=color, linestyle=style, linewidth=1.8, marker="o", markersize=3.5, markeredgecolor="white", markeredgewidth=0.8)
        nudge = {("random", "push one by one"): 9, ("random", "heapify in one pass"): -9}.get((order, method), 0)
        ax.annotate(f"{method}, {order} input", (BUILD_SIZES[-1], values[-1]), xytext=(6, nudge), textcoords="offset points", fontsize=8, color=color, va="center")
    ax.set_xscale("log")
    plain_numbers(ax.xaxis)
    ax.set_ylim(0, None)
    ax.set_xlabel("items in the heap (log scale)")
    ax.set_ylabel("comparisons per item")
    ax.set_title("Building a heap: one item at a time, or all at once")
    fig.subplots_adjust(right=0.64)
    save(fig, SLUG, "build")


if __name__ == "__main__":
    path = Path(__file__).parent / "results" / f"{SLUG}.json"
    if "--charts-only" in sys.argv:
        results = json.loads(path.read_text())
    else:
        results = compute()
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(results, indent=2))
        print(f"  wrote {path.name}")
    draw_array_tree()
    draw_sift()
    draw_top_k(results)
    draw_build(results)
