"""How a hash table works, and why dict lookups are fast.

Article: https://chekh.dev/writing/how-a-hash-table-works-and-why-dict-lookups-are-fast/
Run:     uv run python hash_table.py                 (about a minute)
         uv run python hash_table.py --charts-only   (redraw from results/)
         uv run pytest tests/test_hash_table.py

A hash table in plain Python — buckets, a hash function, chaining, resizing — timed
against a list scan and Python's own dict as the table grows, then with resizing
switched off, then with a deliberately bad hash function.
"""

import json
import random
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from matplotlib.ticker import NullFormatter

from _common import ACCENT, INK, INK_2, MUTED, machine, plain_numbers, save, seconds, time_axis, time_per_call

SLUG = "how-a-hash-table-works-and-why-dict-lookups-are-fast"
SIZES = [1_000 * 2**k for k in range(9)]  # 1,000 … 256,000
LOADS = [0.5, 1, 2, 4, 8, 16, 32, 64]


def simple_hash(key) -> int:
    """A textbook string hash: walk the characters, multiply, add.

    Deterministic, unlike Python's own hash for strings, which is salted per process.
    """
    h = 0
    for ch in str(key):
        h = (h * 31 + ord(ch)) % 2**32
    return h


class HashMap:
    """A hash table with separate chaining: a list of buckets, each a list of
    (key, value) pairs."""

    def __init__(self, capacity=8, hash_function=hash, resize=True):
        self.buckets: list[list] = [[] for _ in range(capacity)]
        self.size = 0
        self.hash_function = hash_function
        self.resize = resize

    def _bucket(self, key) -> list:
        return self.buckets[self.hash_function(key) % len(self.buckets)]

    def get(self, key, default=None):
        for k, v in self._bucket(key):  # only this bucket is searched
            if k == key:
                return v
        return default

    def put(self, key, value) -> None:
        bucket = self._bucket(key)
        for i, (k, _) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)
                return
        bucket.append((key, value))
        self.size += 1
        if self.resize and self.size > 0.75 * len(self.buckets):
            self._grow()

    def delete(self, key) -> bool:
        bucket = self._bucket(key)
        for i, (k, _) in enumerate(bucket):
            if k == key:
                del bucket[i]
                self.size -= 1
                return True
        return False

    def _grow(self) -> None:
        """Double the buckets and put every entry back where it now belongs."""
        old = self.buckets
        self.buckets = [[] for _ in range(2 * len(old))]
        for bucket in old:
            for key, value in bucket:
                self._bucket(key).append((key, value))

    @property
    def load_factor(self) -> float:
        return self.size / len(self.buckets)

    def longest_chain(self) -> int:
        return max(len(b) for b in self.buckets)

    def __len__(self) -> int:
        return self.size

    def __contains__(self, key) -> bool:
        return any(k == key for k, _ in self._bucket(key))


def compute() -> dict:
    results: dict = {"machine": machine(), "sizes": SIZES, "lookups": {}, "load": {}, "bad_hash": {}}
    rng = random.Random(0)

    # 1 · Lookup time as the table grows: a list scan, our table, Python's dict.
    for n in SIZES:
        keys = [f"key{i}" for i in range(n)]
        as_list, ours, theirs = list(keys), HashMap(), dict.fromkeys(keys, 0)
        for key in keys:
            ours.put(key, 0)
        probe = rng.sample(keys, 100)  # existing keys; the list scan finds them part-way
        for name, fn in [("list scan", lambda: [k in as_list for k in probe]), ("HashMap", lambda: [ours.get(k) for k in probe]), ("dict", lambda: [theirs[k] for k in probe])]:
            results["lookups"].setdefault(name, []).append(time_per_call(fn) / 100)
        print(f"n = {n:>8,}   list scan {seconds(results['lookups']['list scan'][-1]):>7}   HashMap {seconds(results['lookups']['HashMap'][-1]):>7}   dict {seconds(results['lookups']['dict'][-1]):>7}   longest chain {ours.longest_chain()}")

    # 2 · What resizing is for: the same table with growth switched off.
    for resize in (True, False):
        times, chains = [], []
        table = HashMap(capacity=1_024, resize=resize)
        n = 0
        for load in LOADS:
            target = int(load * 1_024)
            for i in range(n, target):
                table.put(f"key{i}", i)
            n = target
            probe = [f"key{rng.randrange(n)}" for _ in range(100)]
            times.append(time_per_call(lambda: [table.get(k) for k in probe]) / 100)
            chains.append(table.longest_chain())
        results["load"]["resizing" if resize else "fixed at 1,024 buckets"] = {"loads": LOADS, "seconds": times, "longest_chain": chains}
        print(f"{'resizing' if resize else 'fixed capacity':16s} " + "  ".join(f"load {l:>2g}: {seconds(t):>6}" for l, t in zip(LOADS, times)))

    # 3 · A bad hash function puts everything in one bucket.
    n = 10_000
    keys = [f"key{i}" for i in range(n)]
    probe = rng.sample(keys, 100)
    for name, fn in [("Python's hash", hash), ("length of the key", len), ("always 1", lambda key: 1)]:
        table = HashMap(hash_function=fn)
        for key in keys:
            table.put(key, 0)
        t = time_per_call(lambda: [table.get(k) for k in probe]) / 100
        results["bad_hash"][name] = {"seconds": t, "longest_chain": table.longest_chain(), "buckets_used": sum(1 for b in table.buckets if b)}
        print(f"hash = {name:18s} lookup {seconds(t):>7}   longest chain {table.longest_chain():>6,}   buckets in use {results['bad_hash'][name]['buckets_used']:,}")
    return results


def draw_buckets() -> None:
    """Six keys into eight buckets with the textbook hash: one collision, chained."""
    keys = ["ada", "grace", "linus", "guido", "ken", "barbara"]
    table = HashMap(capacity=8, hash_function=simple_hash, resize=False)
    for key in keys:
        table.put(key, len(key))
    fig, ax = plt.subplots(figsize=(7.4, 4.5))
    ax.set_xlim(-0.9, 7.4)
    ax.set_ylim(-4.35, 0.75)
    ax.axis("off")
    for b, bucket in enumerate(table.buckets):
        x = b * 0.9
        ax.add_patch(plt.Rectangle((x, 0), 0.8, 0.55, facecolor="#faf9f6", edgecolor=MUTED, linewidth=1))
        ax.text(x + 0.4, 0.27, str(b), ha="center", va="center", fontsize=9, color=INK_2)
        for depth, (key, _) in enumerate(bucket):
            y = -0.85 - depth * 0.85
            ax.add_patch(plt.Rectangle((x, y), 0.8, 0.55, facecolor="#faf9f6", edgecolor=ACCENT if depth else MUTED, linewidth=1.2 if depth else 1))
            ax.text(x + 0.4, y + 0.27, key, ha="center", va="center", fontsize=8.5, color=INK)
            ax.add_patch(FancyArrowPatch((x + 0.4, y + 0.85), (x + 0.4, y + 0.58), arrowstyle="-|>", mutation_scale=8, color=MUTED, linewidth=1))
    ax.text(-0.1, 0.27, "bucket", ha="right", va="center", fontsize=8.5, color=INK_2)
    ax.text(0, -2.35, "where each key went:", fontsize=8.5, color=INK, va="top")
    for i, key in enumerate(keys):
        h = simple_hash(key)
        ax.text(0, -2.7 - i * 0.27, f"{key:8s} hash {h:>13,}   mod 8 = {h % 8}", fontsize=7.5, color=INK_2, family="monospace", va="top")
    ax.text(4.2, -2.35, '"guido" and "ada" both land in bucket 6: a collision.\nThe bucket keeps both, one after the other, and a lookup\nfor either walks that short chain.', fontsize=8.5, color=INK_2, va="top", linespacing=1.4)
    ax.set_title("Six keys, eight buckets: each key goes where its hash says", fontsize=10.5, loc="left")
    save(fig, SLUG, "buckets")


def draw_lookups(results: dict) -> None:
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    colors = {"list scan": INK_2, "HashMap": INK, "dict": ACCENT}
    for name, times in results["lookups"].items():
        ax.plot(SIZES, times, color=colors[name], linewidth=2 if name == "dict" else 1.6, marker="o", markersize=3.5, markeredgecolor="white", markeredgewidth=0.8)
        ax.annotate({"list scan": "list scan, O(n)", "HashMap": "HashMap, in Python", "dict": "dict, in C"}[name], (SIZES[-1], times[-1]), xytext=(6, 0), textcoords="offset points", fontsize=8.5, color=colors[name], va="center")
    ax.set_xscale("log")
    ax.set_yscale("log")
    plain_numbers(ax.xaxis)
    time_axis(ax.yaxis)
    ax.set_xlim(800, 6e5)
    ax.set_xlabel("keys in the table (log scale)")
    ax.set_ylabel("time per lookup (log scale)")
    ax.set_title("Finding one key as the table grows")
    fig.subplots_adjust(right=0.74)
    save(fig, SLUG, "lookups")


def draw_load(results: dict) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for name, run in results["load"].items():
        color = ACCENT if name == "resizing" else INK_2
        ax.plot(run["loads"], run["seconds"], color=color, linewidth=1.8, marker="o", markersize=3.5, markeredgecolor="white", markeredgewidth=0.8)
        ax.annotate(name, (run["loads"][-1], run["seconds"][-1]), xytext=(6, 0), textcoords="offset points", fontsize=8.5, color=color, va="center")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xticks(LOADS, [f"{l:g}" for l in LOADS])
    ax.set_yticks([3e-7, 5e-7, 1e-6, 2e-6])
    ax.yaxis.set_minor_formatter(NullFormatter())
    time_axis(ax.yaxis)
    ax.set_xlim(0.4, 130)
    ax.set_xlabel("load factor: entries per bucket, if the table never grew")
    ax.set_ylabel("time per lookup (log scale)")
    ax.set_title("Why the table doubles itself at three-quarters full")
    fig.subplots_adjust(right=0.8)
    save(fig, SLUG, "load")


if __name__ == "__main__":
    path = Path(__file__).parent / "results" / f"{SLUG}.json"
    if "--charts-only" in sys.argv:
        results = json.loads(path.read_text())
    else:
        results = compute()
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(results, indent=2))
        print(f"  wrote {path.name}")
    draw_buckets()
    draw_lookups(results)
    draw_load(results)
