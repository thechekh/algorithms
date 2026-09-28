"""Arrays and linked lists: what "fast" depends on.

Article: https://chekh.dev/writing/arrays-and-linked-lists-what-fast-depends-on/
Run:     uv run python arrays_and_lists.py                (about two minutes)
         uv run python arrays_and_lists.py --charts-only  (redraw from results/)
         uv run pytest tests/test_arrays_and_lists.py

A singly linked list in plain Python against Python's list, which is an array of
pointers, and collections.deque, a linked list of 64-slot blocks: reading the middle,
inserting at the front and in the middle, and a full scan, timed as they grow. Then the
memory each costs per item, how a list grows, and what memory order does to one sum.
"""

import array
import json
import random
import sys
import time
import tracemalloc
from collections import deque
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from _common import ACCENT, INK, INK_2, MUTED, machine, plain_numbers, save, seconds, time_axis, time_per_call

SLUG = "arrays-and-linked-lists-what-fast-depends-on"
SIZES = [1_000, 10_000, 100_000, 1_000_000]


class Node:
    __slots__ = ("value", "next")

    def __init__(self, value, next=None):
        self.value, self.next = value, next


class LinkedList:
    """A singly linked list: each node holds a value and a pointer to the next one."""

    def __init__(self, values=()):
        self.head = self.tail = None
        self.size = 0
        for value in values:
            self.append(value)

    def push_front(self, value) -> None:
        self.head = Node(value, self.head)  # O(1): nothing else moves
        if self.tail is None:
            self.tail = self.head
        self.size += 1

    def pop_front(self):
        node = self.head
        self.head = node.next
        if self.head is None:
            self.tail = None
        self.size -= 1
        return node.value

    def append(self, value) -> None:
        node = Node(value)
        if self.tail is None:
            self.head = self.tail = node
        else:
            self.tail.next = node  # O(1) because the list keeps a pointer to its tail
            self.tail = node
        self.size += 1

    def node_at(self, index: int) -> Node:
        node = self.head
        for _ in range(index):  # O(n): the only way in is to follow the pointers
            node = node.next
        return node

    def insert_after(self, node: Node, value) -> None:
        node.next = Node(value, node.next)  # O(1) once you are standing on the node
        if self.tail is node:
            self.tail = node.next
        self.size += 1

    def remove_after(self, node: Node):
        removed = node.next
        node.next = removed.next
        if self.tail is removed:
            self.tail = node
        self.size -= 1
        return removed.value

    def __iter__(self):
        node = self.head
        while node:
            yield node.value
            node = node.next

    def __len__(self) -> int:
        return self.size


def operations(n: int) -> dict:
    """Each operation on each structure, as a zero-argument function that leaves it as it was."""
    values = list(range(n))
    as_list, as_deque, as_linked = list(values), deque(values), LinkedList(values)
    middle = n // 2
    before_middle = as_linked.node_at(middle - 1)

    def list_front():
        as_list.insert(0, -1)
        del as_list[0]

    def deque_front():
        as_deque.appendleft(-1)
        as_deque.popleft()

    def linked_front():
        as_linked.push_front(-1)
        as_linked.pop_front()

    def list_middle():
        as_list.insert(middle, -1)
        del as_list[middle]

    def deque_middle():
        as_deque.insert(middle, -1)
        del as_deque[middle]

    def linked_middle():  # walk to the spot, then the O(1) insert
        node = as_linked.node_at(middle - 1)
        as_linked.insert_after(node, -1)
        as_linked.remove_after(node)

    return {
        "read the middle item": {"list": lambda: as_list[middle], "deque": lambda: as_deque[middle],
                                 "linked list": lambda: as_linked.node_at(middle).value},
        "insert and remove at the front": {"list": list_front, "deque": deque_front, "linked list": linked_front},
        "insert and remove in the middle": {"list": list_middle, "deque": deque_middle, "linked list": linked_middle},
        "sum every item": {"list": lambda: sum(as_list), "deque": lambda: sum(as_deque),
                           "linked list": lambda: sum(as_linked)},
        "_already_at_middle": before_middle,
    }


def bytes_per_item(n: int = 200_000) -> dict:
    """Extra memory to hold n existing ints, per item, measured with tracemalloc."""
    values = list(range(10**6, 10**6 + n))  # the int objects exist before we start
    builders = {
        "list": lambda: list(values),
        "list built by appending": lambda: [v for v in values],
        "deque": lambda: deque(values),
        "linked list": lambda: LinkedList(values),
        "array.array('q')": lambda: array.array("q", values),
        "numpy int64": lambda: np.array(values, dtype=np.int64),
    }
    out = {}
    for name, build in builders.items():
        tracemalloc.start()
        before = tracemalloc.get_traced_memory()[0]
        kept = build()
        after = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()
        out[name] = (after - before) / n
        del kept
    out["the int objects themselves"] = sys.getsizeof(values[0])
    return out


def list_capacity(lst: list) -> int:
    """Pointers the list has room for: its size, less an empty list's, over 8."""
    return (sys.getsizeof(lst) - sys.getsizeof([])) // 8


def growth(limit: int = 200) -> list[tuple[int, int]]:
    lst, steps = [], []
    for i in range(limit):
        lst.append(i)
        steps.append((len(lst), list_capacity(lst)))
    return steps


def memory_order(n: int = 5_000_000, repeats: int = 5) -> dict:
    """The same sum, visiting memory in order and in a random order."""
    rng = np.random.default_rng(0)
    a = np.arange(n, dtype=np.int64)
    in_order = np.arange(n)
    shuffled = rng.permutation(n)
    out = {}
    for name, index in [("numpy, in memory order", in_order), ("numpy, random order", shuffled)]:
        best = min(_timed(lambda: a[index].sum()) for _ in range(repeats))
        out[name] = best
    ints = [10**6 + i for i in range(n)]  # int objects allocated one after another
    mixed = ints[:]
    random.Random(0).shuffle(mixed)  # the same objects, pointers in a random order
    for name, lst in [("Python list, objects in memory order", ints), ("Python list, objects in random order", mixed)]:
        out[name] = min(_timed(lambda: sum(lst)) for _ in range(repeats))
    return out


def _timed(fn) -> float:
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


def compute() -> dict:
    results: dict = {"machine": machine(), "sizes": SIZES, "timings": {}}
    for n in SIZES:
        ops = operations(n)
        ops.pop("_already_at_middle")
        for op, impls in ops.items():
            for name, fn in impls.items():
                results["timings"].setdefault(op, {}).setdefault(name, []).append(time_per_call(fn, repeats=3))
        print(f"n = {n:>9,}   " + "   ".join(f"{op[:18]}: " + " ".join(f"{k[:6]} {seconds(v[-1]):>7}" for k, v in impls.items())
                                              for op, impls in ((o, {k: results['timings'][o][k] for k in results['timings'][o]}) for o in results["timings"])))
    results["bytes_per_item"] = bytes_per_item()
    print("bytes per item:", {k: round(v, 1) for k, v in results["bytes_per_item"].items()})
    results["growth"] = growth()
    capacities = sorted({c for _, c in results["growth"]})
    print("list capacities while appending:", capacities[:16], "...")
    results["memory_order"] = memory_order()
    print("memory order:", {k: seconds(v) for k, v in results["memory_order"].items()})
    return results


# --- Charts ------------------------------------------------------------------------------


def draw_memory() -> None:
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    ax.set_xlim(0, 12.2)
    ax.set_ylim(-0.4, 6.0)
    ax.axis("off")

    def cell(x, y, text, w=0.7, h=0.5, fill="#faf9f6", accent=False, fontsize=8):
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=ACCENT if accent else fill, edgecolor=INK_2, linewidth=0.9))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, color="white" if accent else INK)

    ax.text(0, 5.9, "Python list: one block of pointers, each to an int object elsewhere", fontsize=8.8, color=INK, va="top")
    for i in range(6):
        cell(0.3 + i * 0.7, 4.6, "", fill="#dfe5df")
        ax.annotate("", (1.0 + i * 1.75, 3.75), (0.65 + i * 0.7, 4.62), arrowprops={"arrowstyle": "-|>", "color": MUTED, "linewidth": 0.8})
        cell(0.7 + i * 1.75, 3.25, str(i * 10), w=0.6)
    ax.text(4.75, 4.85, "list[3] = start + 3 × 8 bytes: one step", fontsize=7.8, color=ACCENT, va="center")

    ax.text(0, 2.75, "array.array or numpy: the values themselves, side by side", fontsize=8.8, color=INK, va="top")
    for i in range(6):
        cell(0.3 + i * 0.7, 1.75, str(i * 10), fill="#dfe5df")

    ax.text(6.2, 2.75, "linked list: nodes anywhere, each pointing to the next", fontsize=8.8, color=INK, va="top")
    spots = [(6.3, 1.7), (7.5, 0.35), (8.7, 1.85), (9.9, 0.7), (11.1, 1.55)]
    for i, (x, y) in enumerate(spots):
        cell(x, y, str(i * 10), w=0.55)
        cell(x + 0.55, y, "", w=0.35, fill="#dfe5df")
        if i + 1 < len(spots):
            nx, ny = spots[i + 1]
            ax.annotate("", (nx, ny + 0.25), (x + 0.75, y + 0.25), arrowprops={"arrowstyle": "-|>", "color": INK_2, "linewidth": 0.9,
                                                                               "connectionstyle": "arc3,rad=0.2"})
    ax.text(5.35, 1.95, "head", fontsize=7.8, color=INK_2, va="center")
    ax.annotate("", (6.28, 1.95), (5.85, 1.95), arrowprops={"arrowstyle": "-|>", "color": INK_2, "linewidth": 0.9})
    ax.text(6.2, -0.3, "to reach item 3, follow three pointers from the head", fontsize=7.8, color=INK_2, va="center")
    save(fig, SLUG, "memory")


def draw_timings(results: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(8.4, 5.6), sharex=True)
    colors = {"list": ACCENT, "deque": INK, "linked list": INK_2}
    for ax, (op, impls) in zip(axes.flat, results["timings"].items()):
        for name, times in impls.items():
            ax.plot(SIZES, times, color=colors[name], linewidth=2 if name == "list" else 1.6, marker="o", markersize=3.5,
                    markeredgecolor="white", markeredgewidth=0.8, label=name)
        ax.set_xscale("log")
        ax.set_yscale("log")
        plain_numbers(ax.xaxis)
        time_axis(ax.yaxis)
        ax.set_title(op, fontsize=9.5, loc="left")
    for ax in axes[1]:
        ax.set_xlabel("items (log scale)")
    axes[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle("Time per operation as the structure grows (log-log)", fontsize=10.5)
    fig.tight_layout()
    save(fig, SLUG, "timings")


def draw_growth(results: dict) -> None:
    lengths, capacities = zip(*results["growth"])
    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    ax.step(lengths, capacities, where="post", color=ACCENT, linewidth=1.8, label="room the list has")
    ax.plot(lengths, lengths, color=MUTED, linewidth=1, linestyle="--", label="items in it")
    ax.set_xlabel("items appended one at a time")
    ax.set_ylabel("slots")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("A list over-allocates, so most appends need no copying", fontsize=10)
    save(fig, SLUG, "growth")


if __name__ == "__main__":
    path = Path(__file__).parent / "results" / f"{SLUG}.json"
    if "--charts-only" in sys.argv:
        results = json.loads(path.read_text())
    else:
        results = compute()
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(results, indent=1))
        print(f"  wrote {path.name}")
    draw_memory()
    draw_timings(results)
    draw_growth(results)
