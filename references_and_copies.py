"""Memory: references, copies and what Python hides.

Article: https://chekh.dev/writing/memory-references-copies-and-what-python-hides/
Run:     uv run python references_and_copies.py                (about ten seconds)
         uv run python references_and_copies.py --charts-only  (redraw from results/)
         uv run pytest tests/test_references_and_copies.py

Names and the objects they refer to: two names for one list, the list-of-lists trap, the
default argument that remembers, shallow and deep copies compared and timed, what
sys.getsizeof leaves out, and when reference counting and the cycle collector free an
object.
"""

import copy
import gc
import json
import pickle
import sys
import tracemalloc
import weakref
from pathlib import Path

import matplotlib.pyplot as plt

from _common import ACCENT, DANGER, INK, INK_2, MUTED, machine, plain_numbers, save, seconds, time_axis, time_per_call

SLUG = "memory-references-copies-and-what-python-hides"


# --- Names and objects ----------------------------------------------------------------------


def two_names() -> dict:
    a = [1, 2, 3]
    b = a  # a second name for the same list: nothing is copied
    b.append(4)
    c = list(a)  # a new list, holding the same four items
    c.append(5)
    return {"a": a, "b": b, "c": c, "a is b": a is b, "a is c": a is c, "a[0] is c[0]": a[0] is c[0]}


def rows_trap() -> dict:
    shared = [[0] * 3] * 3  # three references to one row
    separate = [[0] * 3 for _ in range(3)]  # three rows
    shared[0][0] = 1
    separate[0][0] = 1
    return {"shared": shared, "separate": separate,
            "rows in shared": len({id(row) for row in shared}),
            "rows in separate": len({id(row) for row in separate})}


def default_argument() -> dict:
    def append_to(item, bucket=[]):  # made once, when def runs
        bucket.append(item)
        return bucket

    def append_to_fixed(item, bucket=None):
        if bucket is None:
            bucket = []  # a new list on every call that needs one
        bucket.append(item)
        return bucket

    return {"append_to": [list(append_to(i)) for i in (1, 2, 3)],
            "append_to_fixed": [list(append_to_fixed(i)) for i in (1, 2, 3)]}


def arguments() -> dict:
    def add_item(items):
        items.append("new")  # changes the object the caller passed in

    def replace_items(items):
        items = ["new"]  # moves the local name; the caller sees nothing
        return items

    mine = ["old"]
    add_item(mine)
    after_add = list(mine)
    replace_items(mine)
    return {"after add_item": after_add, "after replace_items": list(mine)}


def tuple_holding_a_list() -> dict:
    pair = ([1, 2], "label")
    pair[0].append(3)  # the tuple cannot change, but the list inside it can
    try:
        hash(pair)
        hashable = True
    except TypeError as e:
        hashable = str(e)
    return {"pair": repr(pair), "hash(pair)": hashable}


# --- Copies ---------------------------------------------------------------------------------


def copies() -> dict:
    original = [[1, 2], [3, 4]]
    shallow = copy.copy(original)  # a new outer list, the same rows
    deep = copy.deepcopy(original)  # a new outer list and new rows
    original[0].append(99)
    return {"original": original, "shallow": shallow, "deep": deep,
            "shallow shares rows": shallow[0] is original[0], "deep shares rows": deep[0] is original[0]}


COPIERS = {
    "list(grid)": list,
    "[row[:] for row in grid]": lambda grid: [row[:] for row in grid],
    "copy.deepcopy(grid)": copy.deepcopy,
    "pickle round trip": lambda grid: pickle.loads(pickle.dumps(grid, protocol=pickle.HIGHEST_PROTOCOL)),
}


def copy_timings(sizes: list[int]) -> dict:
    """Seconds per row to copy a grid of n rows of 10 numbers, four ways."""
    out = {name: [] for name in COPIERS}
    for n in sizes:
        grid = [[10 * i + j for j in range(10)] for i in range(n)]
        for name, copier in COPIERS.items():
            out[name].append(time_per_call(lambda: copier(grid), repeats=3) / n)
        print(f"n = {n:>7,} rows: " + "  ".join(f"{k}: {seconds(v[-1])}/row" for k, v in out.items()))
    return out


# --- What sys.getsizeof leaves out ----------------------------------------------------------


def deep_size(obj, seen: set | None = None) -> int:
    """getsizeof of an object and everything it refers to, each counted once."""
    seen = set() if seen is None else seen
    if id(obj) in seen:
        return 0
    seen.add(id(obj))
    if isinstance(obj, dict):
        children = [*obj.keys(), *obj.values()]
    elif isinstance(obj, (list, tuple, set, frozenset)):
        children = obj
    else:
        children = ()
    return sys.getsizeof(obj) + sum(deep_size(child, seen) for child in children)


BUILDERS = {
    "1,000 numbers in a list": lambda: [10**6 + i for i in range(1_000)],
    "1,000 short strings in a list": lambda: [f"user-{i:05d}" for i in range(1_000)],
    "a dict of 1,000 strings to numbers": lambda: {f"user-{i:05d}": 10**6 + i for i in range(1_000)},
    "1,000 rows of 10 numbers": lambda: [[10**6 + 10 * i + j for j in range(10)] for i in range(1_000)],
}


def sizes() -> dict:
    out = {}
    for name, build in BUILDERS.items():
        tracemalloc.start()
        obj = build()
        allocated = tracemalloc.get_traced_memory()[0]  # everything the build left alive
        tracemalloc.stop()
        out[name] = {"sys.getsizeof": sys.getsizeof(obj), "deep_size": deep_size(obj), "tracemalloc": allocated}
    return out


# --- When objects are freed -----------------------------------------------------------------


def refcounts() -> list:
    """sys.getrefcount after each step; it counts its own argument, so one more than the names."""
    steps = []
    obj = []
    steps.append(("obj = []", sys.getrefcount(obj)))
    alias = obj
    steps.append(("alias = obj", sys.getrefcount(obj)))
    box = [obj]
    steps.append(("box = [obj]", sys.getrefcount(obj)))
    del alias
    steps.append(("del alias", sys.getrefcount(obj)))
    box.clear()
    steps.append(("box.clear()", sys.getrefcount(obj)))
    return steps


def hidden() -> dict:
    return {"sys.getrefcount(None)": sys.getrefcount(None), "sys.getrefcount(1)": sys.getrefcount(1),
            "int('256') is int('256')": int("256") is int("256"),
            "int('257') is int('257')": int("257") is int("257"),
            "int('257') == int('257')": int("257") == int("257")}


class Box:
    """An object that can point at another one."""

    def __init__(self):
        self.other = None


def lifetimes() -> dict:
    """When is an object freed? Watched with weakref.finalize, automatic collection paused."""
    events: list[str] = []
    gc.disable()
    gc.collect()  # start from a clean slate, so the count below is this cycle alone
    try:
        single = Box()
        weakref.finalize(single, events.append, "single freed")
        del single  # the last reference goes: freed on the spot
        after_single = list(events)
        first, second = Box(), Box()
        first.other, second.other = second, first  # a cycle: each keeps the other alive
        weakref.finalize(first, events.append, "cycle freed")
        del first, second
        after_cycle = list(events)
        found = gc.collect()  # the cycle collector finds what reference counting cannot
        after_collect = list(events)
    finally:
        gc.enable()
    return {"after del, no cycle": after_single, "after del, cycle": after_cycle,
            "after gc.collect()": after_collect, "gc.collect() returned": found}


def compute() -> dict:
    results: dict = {"machine": machine()}
    for name, fn in [("two names", two_names), ("rows trap", rows_trap), ("default argument", default_argument),
                     ("arguments", arguments), ("tuple holding a list", tuple_holding_a_list), ("copies", copies),
                     ("refcounts", refcounts), ("hidden", hidden), ("lifetimes", lifetimes)]:
        results[name] = fn()
        print(f"{name}: {results[name]}")
    results["sizes"] = sizes()
    for name, v in results["sizes"].items():
        print(f"  {name:36s} getsizeof {v['sys.getsizeof']:>7,}  deep_size {v['deep_size']:>7,}  tracemalloc {v['tracemalloc']:>7,}")
    results["copy sizes"] = [10, 100, 1_000, 10_000, 100_000]
    results["copy timings"] = copy_timings(results["copy sizes"])
    return results


# --- Charts ---------------------------------------------------------------------------------

LIGHT, PALE = "#dfe5df", "#faf9f6"


def _slots(ax, x, y, n, w=0.55, h=0.5, fill=LIGHT):
    for i in range(n):
        ax.add_patch(plt.Rectangle((x + i * w, y), w, h, facecolor=fill, edgecolor=INK_2, linewidth=0.9))
    return [(x + i * w + w / 2, y + h / 2) for i in range(n)]


def _value(ax, x, y, text, w=0.5, h=0.45, color=INK):
    ax.add_patch(plt.Rectangle((x - w / 2, y - h / 2), w, h, facecolor=PALE, edgecolor=INK_2, linewidth=0.9))
    ax.text(x, y, text, ha="center", va="center", fontsize=8.5, color=color)


def _arrow(ax, start, end, color=MUTED, rad=0.0, lw=0.9):
    ax.annotate("", end, start, arrowprops={"arrowstyle": "-|>", "color": color, "linewidth": lw,
                                            "connectionstyle": f"arc3,rad={rad}", "shrinkA": 0, "shrinkB": 2})


def _name(ax, x, y, text):
    ax.text(x, y, text, ha="right", va="center", fontsize=10.5, color=INK, family="monospace")


def draw_names() -> None:
    """a = [1, 2, 3]; b = a; c = list(a): three names, two lists, one set of numbers."""
    fig, ax = plt.subplots(figsize=(7.6, 3.4))
    ax.set_xlim(-0.2, 9.2)
    ax.set_ylim(-0.1, 4.1)
    ax.axis("off")
    ax.text(0, 3.9, "a = [1, 2, 3]\nb = a\nc = list(a)", fontsize=9, color=INK, va="top", family="monospace")
    top = _slots(ax, 3.6, 3.0, 3)
    bottom = _slots(ax, 3.6, 0.3, 3)
    ints = [(x, 1.9) for x, _ in top]
    for (x, y), text in zip(ints, ["1", "2", "3"]):
        _value(ax, x, y, text, w=0.42, h=0.42)
    for (sx, sy), (ix, iy) in zip(top, ints):
        _arrow(ax, (sx, sy), (ix, iy + 0.21))
    for (sx, sy), (ix, iy) in zip(bottom, ints):
        _arrow(ax, (sx, sy), (ix, iy - 0.21))
    for label, y, target, color in [("a", 3.55, (3.6, 3.35), ACCENT), ("b", 2.95, (3.6, 3.12), ACCENT),
                                    ("c", 0.55, (3.6, 0.55), INK_2)]:
        _name(ax, 2.5, y, label)
        _arrow(ax, (2.6, y), target, color=color, lw=1.2)
    ax.text(5.45, 3.25, "one list, two names", fontsize=8.2, color=ACCENT, va="center")
    ax.text(5.45, 1.9, "the int objects 1, 2 and 3", fontsize=8.2, color=INK_2, va="center")
    ax.text(5.45, 0.55, "a second list, pointing at the same numbers", fontsize=8.2, color=INK_2, va="center")
    save(fig, SLUG, "names")


def draw_rows(results: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.5))
    panels = [("grid = [[0] * 3] * 3", results["rows trap"]["shared"], True),
              ("grid = [[0] * 3 for _ in range(3)]", results["rows trap"]["separate"], False)]
    for ax, (title, rows, shared) in zip(axes, panels):
        ax.set_xlim(-0.2, 4.6)
        ax.set_ylim(-0.9, 3.4)
        ax.axis("off")
        ax.text(0, 3.3, title, fontsize=8.8, color=INK, va="top", family="monospace")
        ax.text(0, 2.75, "then grid[0][0] = 1", fontsize=8.2, color=INK_2, va="top")
        outer = [(0.35, 1.85 - i * 0.75) for i in range(3)]
        for (x, y) in outer:
            ax.add_patch(plt.Rectangle((x - 0.25, y - 0.25), 0.5, 0.5, facecolor=LIGHT, edgecolor=INK_2, linewidth=0.9))
        targets = [(2.3, 1.1)] * 3 if shared else [(2.3, 1.85 - i * 0.75) for i in range(3)]
        drawn = set()
        for i, ((x, y), (tx, ty)) in enumerate(zip(outer, targets)):
            _arrow(ax, (x + 0.1, y), (tx - 0.05, ty), color=DANGER if shared else ACCENT, lw=1.1)
            if (tx, ty) not in drawn:
                drawn.add((tx, ty))
                row = rows[0] if shared else rows[i]
                for j, v in enumerate(row):
                    _value(ax, tx + 0.3 + j * 0.5, ty, str(v), w=0.5, h=0.5, color=DANGER if (shared and v == 1) else INK)
        note = ("one row, three references: grid[0],\ngrid[1] and grid[2] all show the 1" if shared
                else "three rows: only grid[0] changes")
        ax.text(0, -0.85, note, fontsize=8.2, color=DANGER if shared else ACCENT, va="bottom")
    save(fig, SLUG, "rows")


def draw_copies() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.2))
    for ax, (title, deep) in zip(axes, [("shallow = copy.copy(original)", False), ("deep = copy.deepcopy(original)", True)]):
        ax.set_xlim(-0.2, 5.0)
        ax.set_ylim(-0.75, 3.4)
        ax.axis("off")
        ax.text(0, 3.3, title, fontsize=8.8, color=INK, va="top", family="monospace")
        ax.text(0.95, 2.35, "original", fontsize=8.5, color=INK, ha="right", va="center")
        ax.text(0.95, 0.75, "deep" if deep else "shallow", fontsize=8.5, color=INK, ha="right", va="center")
        top = _slots(ax, 1.1, 2.1, 2)
        bottom = _slots(ax, 1.1, 0.5, 2)
        rows_top = [(3.2, 2.55), (3.2, 1.75)]
        rows_bottom = [(3.2, 1.0), (3.2, 0.2)] if deep else rows_top
        for (x, y), label in zip(rows_top, ["1, 2", "3, 4"]):
            _value(ax, x + 0.45, y, label, w=0.9, h=0.45)
        if deep:
            for (x, y), label in zip(rows_bottom, ["1, 2", "3, 4"]):
                _value(ax, x + 0.45, y, label, w=0.9, h=0.45)
        for (sx, sy), (tx, ty) in zip(top, rows_top):
            _arrow(ax, (sx, sy), (tx, ty), color=INK_2)
        for (sx, sy), (tx, ty) in zip(bottom, rows_bottom):
            _arrow(ax, (sx, sy), (tx, ty), color=ACCENT if deep else DANGER, rad=0.0 if deep else 0.15)
        note = "new rows: a change to one never reaches the other" if deep else "the same two rows: a change shows in both"
        ax.text(0, -0.7, note, fontsize=8, color=ACCENT if deep else DANGER, va="bottom")
    save(fig, SLUG, "copies")


def draw_copy_times(results: dict) -> None:
    sizes = results["copy sizes"]
    colors = {"list(grid)": MUTED, "[row[:] for row in grid]": ACCENT, "copy.deepcopy(grid)": DANGER,
              "pickle round trip": INK_2}
    fig, ax = plt.subplots(figsize=(6.8, 3.8))
    for name, times in results["copy timings"].items():
        color = colors.get(name, INK)  # a copier added to COPIERS draws in ink
        ax.plot(sizes, times, color=color, linewidth=1.8, marker="o", markersize=3.5, markeredgecolor="white",
                markeredgewidth=0.8)
        ax.text(sizes[-1] * 1.35, times[-1], name, fontsize=8.3, color=color, va="center", family="monospace")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(sizes)
    plain_numbers(ax.xaxis)
    time_axis(ax.yaxis)
    ax.set_xlim(6, 3e7)
    ax.set_xlabel("rows of 10 numbers (log scale)")
    ax.set_ylabel("time per row (log scale)")
    ax.set_title("Copying a list of lists: how deep you go decides the cost", fontsize=10)
    save(fig, SLUG, "copy-times")


if __name__ == "__main__":
    path = Path(__file__).parent / "results" / f"{SLUG}.json"
    if "--charts-only" in sys.argv:
        results = json.loads(path.read_text(encoding="utf-8"))
    else:
        results = compute()
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(results, indent=1), encoding="utf-8")
        print(f"  wrote {path.name}")
    draw_names()
    draw_rows(results)
    draw_copies()
    draw_copy_times(results)
