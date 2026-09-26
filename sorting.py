"""Sorting, from bubble sort to Timsort.

Article: https://chekh.dev/writing/sorting-from-bubble-sort-to-timsort/
Run:     uv run python sorting.py                 (about two minutes)
         uv run python sorting.py --charts-only   (redraw from results/)
         uv run pytest tests/test_sorting.py

Four sorting algorithms in plain Python — bubble, insertion, merge and quick sort —
traced on eight numbers, then timed against Python's built-in sorted() (Timsort) as the
input grows, and on inputs that are already sorted, reversed or nearly sorted.
"""

import json
import random
import sys
from pathlib import Path

import matplotlib.pyplot as plt

from _common import ACCENT, INK, INK_2, MUTED, machine, plain_numbers, save, seconds, time_axis, time_per_call

SLUG = "sorting-from-bubble-sort-to-timsort"


def bubble_sort(items: list) -> list:
    """Sweep through, swapping neighbours that are out of order, until a sweep swaps nothing."""
    items = list(items)
    n = len(items)
    for sweep in range(n - 1):
        swapped = False
        for i in range(n - 1 - sweep):  # the last `sweep` elements are already in place
            if items[i] > items[i + 1]:
                items[i], items[i + 1] = items[i + 1], items[i]
                swapped = True
        if not swapped:
            return items
    return items


def insertion_sort(items: list) -> list:
    """Grow a sorted prefix: take the next element and slide it left to where it belongs."""
    items = list(items)
    for i in range(1, len(items)):
        value = items[i]
        j = i - 1
        while j >= 0 and items[j] > value:
            items[j + 1] = items[j]  # shift the larger element right
            j -= 1
        items[j + 1] = value
    return items


def merge_sort(items: list) -> list:
    """Split in half, sort each half, then merge the two sorted halves."""
    if len(items) <= 1:
        return list(items)
    middle = len(items) // 2
    return merge(merge_sort(items[:middle]), merge_sort(items[middle:]))


def merge(left: list, right: list) -> list:
    """Interleave two sorted lists into one, always taking the smaller front element."""
    merged, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:  # <= keeps equal elements in their original order
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    return merged + left[i:] + right[j:]


def quick_sort(items: list, pivot_at: str = "middle") -> list:
    """Pick a pivot, split into smaller / equal / larger, sort the two sides, join."""
    if len(items) <= 1:
        return list(items)
    pivot = items[len(items) // 2] if pivot_at == "middle" else items[0]
    smaller = [x for x in items if x < pivot]
    equal = [x for x in items if x == pivot]
    larger = [x for x in items if x > pivot]
    return quick_sort(smaller, pivot_at) + equal + quick_sort(larger, pivot_at)


ALGORITHMS = {
    "bubble sort": bubble_sort,
    "insertion sort": insertion_sort,
    "merge sort": merge_sort,
    "quick sort": quick_sort,
    "sorted() — Timsort": sorted,
}
QUADRATIC = {"bubble sort", "insertion sort"}
SIZES = [500 * 2**k for k in range(11)]  # 500 … 512,000
SCENARIO_N = 5_000


def inputs(n: int) -> dict[str, list[int]]:
    rng = random.Random(0)
    shuffled = list(range(n))
    rng.shuffle(shuffled)
    nearly = list(range(n))
    for _ in range(n // 100):  # 1% of positions swapped with a neighbour
        i = rng.randrange(n - 1)
        nearly[i], nearly[i + 1] = nearly[i + 1], nearly[i]
    return {"random": shuffled, "already sorted": list(range(n)), "reversed": list(range(n, 0, -1)), "nearly sorted": nearly}


def compute() -> dict:
    results = {"machine": machine(), "timings": {}, "scenarios": {}, "scenario_n": SCENARIO_N}
    for name, algorithm in ALGORITHMS.items():
        sizes = [n for n in SIZES if n <= 8_000] if name in QUADRATIC else SIZES
        times = []
        for n in sizes:
            data = inputs(n)["random"]
            times.append(time_per_call(lambda: algorithm(data)))
        results["timings"][name] = {"sizes": sizes, "seconds": times}
        print(f"{name:20s} " + "  ".join(f"{n:>7,}: {seconds(t):>7}" for n, t in zip(sizes, times)))

    data = inputs(SCENARIO_N)
    scenario_algorithms = dict(ALGORITHMS)
    scenario_algorithms["quick sort, first-element pivot"] = lambda items: quick_sort(items, pivot_at="first")
    for name, algorithm in scenario_algorithms.items():
        row = {}
        for label, items in data.items():
            try:
                row[label] = time_per_call(lambda: algorithm(items))
            except RecursionError:
                row[label] = None  # the recursion went deeper than Python allows
        results["scenarios"][name] = row
        print(f"{name:34s} " + "  ".join(f"{label}: {seconds(t) if t is not None else 'RecursionError':>14}" for label, t in row.items()))
    return results


# --- traces on eight numbers ------------------------------------------------------

EIGHT = [5, 2, 9, 1, 7, 3, 8, 6]


def _row(ax, values, y, states, width=0.9, gap=0.1):
    """Draw one row of boxes. states[i] is 'plain', 'active', 'done' or 'gap'."""
    x = 0.0
    for value, state in zip(values, states):
        if state == "gap":
            x += width * 0.5
            continue
        face = {"plain": "none", "active": ACCENT, "done": "#e4e4da"}[state]
        edge = {"plain": MUTED, "active": ACCENT, "done": MUTED}[state]
        ink = "white" if state == "active" else INK
        ax.add_patch(plt.Rectangle((x, y), width, 0.7, facecolor=face, edgecolor=edge, linewidth=1))
        ax.text(x + width / 2, y + 0.35, str(value), ha="center", va="center", fontsize=9, color=ink)
        x += width + gap


def draw_insertion() -> None:
    rows = [(list(EIGHT), ["plain"] * 8, "start")]
    items = list(EIGHT)
    for i in range(1, len(items)):
        value = items[i]
        j = i - 1
        while j >= 0 and items[j] > value:
            items[j + 1] = items[j]
            j -= 1
        items[j + 1] = value
        states = ["done"] * (i + 1) + ["plain"] * (len(items) - i - 1)
        states[j + 1] = "active"
        rows.append((list(items), states, f"take {value}, slide it left into the sorted part"))
    fig, ax = plt.subplots(figsize=(8.0, 0.4 + 0.72 * len(rows)))
    for r, (values, states, note) in enumerate(rows):
        y = -r * 1.0
        _row(ax, values, y, states)
        ax.text(8.4, y + 0.35, note, ha="left", va="center", fontsize=9, color=INK_2 if r else INK)
    ax.set_xlim(-0.2, 15.5)
    ax.set_ylim(-(len(rows) - 1) - 0.5, 1.1)
    ax.axis("off")
    ax.set_title("Insertion sort: the shaded prefix is sorted; the green box was just inserted", fontsize=10, loc="left")
    save(fig, SLUG, "insertion")


def draw_merge() -> None:
    # Levels of the recursion: split down to single elements, then merge back up.
    levels = [[list(EIGHT)]]
    while len(levels[-1][0]) > 1:
        levels.append([part for chunk in levels[-1] for part in (chunk[: len(chunk) // 2], chunk[len(chunk) // 2 :])])
    merged = levels[-1]
    while len(merged) > 1:
        merged = [merge(merged[i], merged[i + 1]) for i in range(0, len(merged), 2)]
        levels.append(merged)
    notes = ["start", "split in half", "and again", "single elements: sorted by definition", "merge pairs", "merge the halves", "sorted"]
    fig, ax = plt.subplots(figsize=(8.0, 0.4 + 0.72 * len(levels)))
    for r, chunks in enumerate(levels):
        y = -r * 1.0
        values, states = [], []
        for c, chunk in enumerate(chunks):
            if c:
                values.append(None)
                states.append("gap")
            values.extend(chunk)
            states.extend(["done" if r >= 3 else "plain"] * len(chunk))
        _row(ax, values, y, states)
        ax.text(11.9, y + 0.35, notes[r], ha="left", va="center", fontsize=9, color=INK_2 if r else INK)
    ax.set_xlim(-0.2, 18.5)
    ax.set_ylim(-(len(levels) - 1) - 0.5, 1.1)
    ax.axis("off")
    ax.set_title("Merge sort: split until every piece is trivially sorted, then merge", fontsize=10, loc="left")
    save(fig, SLUG, "merge")


def draw_quick() -> None:
    # Each level partitions every unfinished piece around its middle element.
    levels = [[("todo", list(EIGHT))]]
    while any(kind == "todo" and len(chunk) > 1 for kind, chunk in levels[-1]):
        next_level = []
        for kind, chunk in levels[-1]:
            if kind != "todo" or len(chunk) <= 1:
                next_level.append(("fixed", chunk))
                continue
            pivot = chunk[len(chunk) // 2]
            for piece in ([x for x in chunk if x < pivot], [pivot], [x for x in chunk if x > pivot]):
                if piece:
                    next_level.append(("pivot" if piece == [pivot] else "todo", piece))
        levels.append(next_level)
    fig, ax = plt.subplots(figsize=(8.0, 0.4 + 0.72 * len(levels)))
    for r, pieces in enumerate(levels):
        y = -r * 1.0
        values, states = [], []
        for p, (kind, chunk) in enumerate(pieces):
            if p:
                values.append(None)
                states.append("gap")
            values.extend(chunk)
            if kind == "pivot":
                states.append("active")
            elif kind == "fixed":
                states.extend(["done"] * len(chunk))
            else:
                states.extend(["plain"] * len(chunk))
        _row(ax, values, y, states)
        note = "start: the middle element, 7, is the pivot" if r == 0 else ("everything in place" if r == len(levels) - 1 else "smaller | pivot | larger, then partition each side")
        ax.text(12.6, y + 0.35, note, ha="left", va="center", fontsize=9, color=INK_2 if r else INK)
    ax.set_xlim(-0.2, 21)
    ax.set_ylim(-(len(levels) - 1) - 0.5, 1.1)
    ax.axis("off")
    ax.set_title("Quick sort: each pivot lands in its final place; green pivots are settled", fontsize=10, loc="left")
    save(fig, SLUG, "quick")


def draw_timings(results: dict) -> None:
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    colors = {"bubble sort": MUTED, "insertion sort": INK_2, "merge sort": INK, "quick sort": INK_2, "sorted() — Timsort": ACCENT}
    for name, entry in results["timings"].items():
        ax.plot(entry["sizes"], entry["seconds"], color=colors[name], linewidth=2 if "Timsort" in name else 1.6, marker="o", markersize=3.5, markeredgecolor="white", markeredgewidth=0.8)
        nudge = {"merge sort": 5, "quick sort": -5}.get(name, 0)  # the two lines end almost together
        ax.annotate(name, (entry["sizes"][-1], entry["seconds"][-1]), xytext=(6, nudge), textcoords="offset points", fontsize=8.5, color=colors[name], va="center")
    ax.set_xscale("log")
    ax.set_yscale("log")
    plain_numbers(ax.xaxis)
    time_axis(ax.yaxis)
    ax.set_xlim(400, 8e5)
    ax.set_xlabel("n, the number of items (log scale)")
    ax.set_ylabel("time to sort (log scale)")
    ax.set_title("Sorting random numbers as the input doubles, ten times")
    fig.subplots_adjust(right=0.74)
    save(fig, SLUG, "timings")


if __name__ == "__main__":
    path = Path(__file__).parent / "results" / f"{SLUG}.json"
    if "--charts-only" in sys.argv:
        results = json.loads(path.read_text())
    else:
        results = compute()
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(results, indent=2))
        print(f"  wrote {path.name}")
    draw_insertion()
    draw_merge()
    draw_quick()
    draw_timings(results)
