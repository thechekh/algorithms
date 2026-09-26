"""Big-O, measured on your laptop.

Article: https://chekh.dev/writing/big-o-measured-on-your-laptop/
Run:     uv run python big_o.py                 (about two minutes)
         uv run python big_o.py --charts-only   (redraw from results/)

Five operations timed as the input doubles from 1,000 to 1,024,000 items, one per
complexity class: a dict lookup (O(1)), a binary search (O(log n)), a scan through a
list (O(n)), a sort (O(n log n)) and a double loop (O(n²)). On log-log axes the slope
of each line is its exponent.
"""

import json
import random
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from _common import ACCENT, INK, INK_2, MUTED, machine, plain_numbers, save, seconds, time_axis, time_per_call
from binary_search import binary_search

SLUG = "big-o-measured-on-your-laptop"
SIZES = [1_000 * 2**k for k in range(11)]  # 1,000 … 1,024,000
QUADRATIC_SIZES = [n for n in SIZES if n <= 16_000]  # beyond this the double loop takes minutes


def count_equal_pairs(items: list[int]) -> int:
    """How many pairs of positions hold the same value. Every pair is compared."""
    count = 0
    n = len(items)
    for i in range(n):
        for j in range(i + 1, n):
            if items[i] == items[j]:
                count += 1
    return count


# Each setup builds an input of size n and returns the operation to time on it.
def setup_dict_lookup(n):
    table = {i: i for i in range(n)}
    key = n // 2
    return lambda: table[key]


def setup_binary_search(n):
    items = list(range(n))
    target = n // 2 + 1
    return lambda: binary_search(items, target)


def setup_scan(n):
    items = list(range(n))
    return lambda: -1 in items  # not there, so every element is checked


def setup_sort(n):
    items = list(range(n))
    random.Random(0).shuffle(items)
    return lambda: sorted(items)


def setup_double_loop(n):
    items = list(range(n))  # all distinct: no early exit, every pair is checked
    return lambda: count_equal_pairs(items)


OPERATIONS = [
    ("dict lookup", "O(1)", setup_dict_lookup, SIZES),
    ("binary search", "O(log n)", setup_binary_search, SIZES),
    ("scan a list", "O(n)", setup_scan, SIZES),
    ("sort", "O(n log n)", setup_sort, SIZES),
    ("double loop", "O(n²)", setup_double_loop, QUADRATIC_SIZES),
]


def compute() -> dict:
    results = {"machine": machine(), "sizes": SIZES, "operations": {}}
    for name, order, setup, sizes in OPERATIONS:
        times = [time_per_call(setup(n)) for n in sizes]
        slope = float(np.polyfit(np.log(sizes), np.log(times), 1)[0])
        entry = {"order": order, "sizes": sizes, "seconds": times, "slope": slope}
        if sizes[-1] < SIZES[-1]:  # extrapolate the quadratic with its own measured slope
            entry["extrapolated"] = {"n": SIZES[-1], "seconds": times[-1] * (SIZES[-1] / sizes[-1]) ** 2}
        results["operations"][name] = entry
        line = "  ".join(f"{n:>9,}: {seconds(t):>8}" for n, t in zip(sizes, times))
        print(f"{name:14s} {order:10s} slope {slope:.2f}\n  {line}")
        if "extrapolated" in entry:
            print(f"  extrapolated to {SIZES[-1]:,}: {seconds(entry['extrapolated']['seconds'])}")
    return results


def draw(results: dict) -> None:
    ops = results["operations"]
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    colors = {"dict lookup": MUTED, "binary search": INK_2, "scan a list": INK, "sort": INK_2, "double loop": ACCENT}
    for name, entry in ops.items():
        sizes, times = entry["sizes"], entry["seconds"]
        ax.plot(sizes, times, color=colors[name], linewidth=2 if name == "double loop" else 1.6, marker="o", markersize=3.5, markeredgecolor="white", markeredgewidth=0.8)
        if "extrapolated" in entry:
            ex = entry["extrapolated"]
            ax.plot([sizes[-1], ex["n"]], [times[-1], ex["seconds"]], color=colors[name], linewidth=1.2, linestyle=(0, (3, 3)))
            ax.annotate(f"{name} {entry['order']}\nslope {entry['slope']:.1f} — {seconds(ex['seconds'])} at 1M, extrapolated",
                        (ex["n"], ex["seconds"]), xytext=(6, 0), textcoords="offset points", fontsize=8.5, color=colors[name], va="center")
        else:
            ax.annotate(f"{name} {entry['order']}, slope {entry['slope']:.1f}", (sizes[-1], times[-1]), xytext=(6, 0), textcoords="offset points", fontsize=8.5, color=colors[name], va="center")
    ax.set_xscale("log")
    ax.set_yscale("log")
    plain_numbers(ax.xaxis)
    time_axis(ax.yaxis)
    ax.set_xlim(800, 1.6e6)
    ax.set_xlabel("n, the size of the input (log scale)")
    ax.set_ylabel("time per call (log scale)")
    ax.set_title("Five operations as the input doubles, ten times")
    fig.subplots_adjust(right=0.62)
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
    draw(results)
