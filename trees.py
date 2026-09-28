"""Binary search trees, balance, and why databases use B-trees.

Article: https://chekh.dev/writing/binary-search-trees-balance-and-why-databases-use-b-trees/
Run:     uv run python trees.py                (about two minutes)
         uv run python trees.py --charts-only  (redraw from results/)
         uv run pytest tests/test_trees.py

A plain binary search tree, an AVL tree that rebalances itself, and a B-tree that keeps
up to 127 keys in each node: their heights as they grow, in random and in sorted order,
and how many nodes a lookup visits in a million keys. Then SQLite, from Python's standard
library, finding one row among a million with and without a B-tree index.
"""

import json
import os
import random
import sqlite3
import sys
import tempfile
import time
from bisect import bisect_left
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from _common import ACCENT, INK, INK_2, MUTED, machine, plain_numbers, save, seconds

SLUG = "binary-search-trees-balance-and-why-databases-use-b-trees"


# --- A plain binary search tree ---------------------------------------------------------------


class Node:
    __slots__ = ("key", "left", "right", "height")

    def __init__(self, key):
        self.key, self.left, self.right, self.height = key, None, None, 1


class BST:
    """Smaller keys to the left, larger to the right, at every node."""

    def __init__(self, keys=()):
        self.root, self.size = None, 0
        for key in keys:
            self.insert(key)

    def insert(self, key) -> None:
        if self.root is None:
            self.root, self.size = Node(key), 1
            return
        node = self.root
        while True:
            if key == node.key:
                return  # already present
            side = "left" if key < node.key else "right"
            child = getattr(node, side)
            if child is None:
                setattr(node, side, Node(key))  # the new key becomes a leaf
                self.size += 1
                return
            node = child

    def search(self, key) -> tuple[bool, int]:
        """Whether the key is there, and how many nodes the search visited."""
        node, visited = self.root, 0
        while node:
            visited += 1
            if key == node.key:
                return True, visited
            node = node.left if key < node.key else node.right
        return False, visited


# --- An AVL tree: a binary search tree that rebalances ---------------------------------------


def _h(node) -> int:
    return node.height if node else 0


def _update(node) -> None:
    node.height = 1 + max(_h(node.left), _h(node.right))


def rotate_right(y: Node) -> Node:
    x = y.left
    y.left, x.right = x.right, y  # x moves up, y becomes its right child
    _update(y)
    _update(x)
    return x


def rotate_left(x: Node) -> Node:
    y = x.right
    x.right, y.left = y.left, x
    _update(x)
    _update(y)
    return y


def avl_insert(node: Node | None, key) -> Node:
    if node is None:
        return Node(key)
    if key < node.key:
        node.left = avl_insert(node.left, key)
    elif key > node.key:
        node.right = avl_insert(node.right, key)
    else:
        return node
    _update(node)
    balance = _h(node.left) - _h(node.right)
    if balance > 1:  # too tall on the left
        if key > node.left.key:
            node.left = rotate_left(node.left)
        return rotate_right(node)
    if balance < -1:  # too tall on the right
        if key < node.right.key:
            node.right = rotate_right(node.right)
        return rotate_left(node)
    return node


class AVL(BST):
    """Every node's two subtrees differ in height by at most one."""

    def insert(self, key) -> None:
        self.root = avl_insert(self.root, key)


# --- A B-tree: many keys per node -----------------------------------------------------------------


class BNode:
    __slots__ = ("keys", "children")

    def __init__(self):
        self.keys, self.children = [], []


class BTree:
    """A B-tree of minimum degree t: every node but the root holds t-1 to 2t-1 sorted keys."""

    def __init__(self, t: int = 64, keys=()):
        self.t, self.root = t, BNode()
        for key in keys:
            self.insert(key)

    def search(self, key) -> tuple[bool, int]:
        node, visited = self.root, 0
        while True:
            visited += 1  # in a database, one visit is one page read
            i = bisect_left(node.keys, key)
            if i < len(node.keys) and node.keys[i] == key:
                return True, visited
            if not node.children:
                return False, visited
            node = node.children[i]

    def insert(self, key) -> None:
        if len(self.root.keys) == 2 * self.t - 1:  # a full root splits, and the tree grows a level
            root = BNode()
            root.children.append(self.root)
            self._split(root, 0)
            self.root = root
        node = self.root
        while True:
            i = bisect_left(node.keys, key)
            if i < len(node.keys) and node.keys[i] == key:
                return
            if not node.children:
                node.keys.insert(i, key)
                return
            if len(node.children[i].keys) == 2 * self.t - 1:  # split full nodes on the way down
                self._split(node, i)
                if key == node.keys[i]:
                    return
                if key > node.keys[i]:
                    i += 1
            node = node.children[i]

    def _split(self, parent: BNode, i: int) -> None:
        t, full, right = self.t, parent.children[i], BNode()
        middle = full.keys[t - 1]
        right.keys, full.keys = full.keys[t:], full.keys[:t - 1]
        if full.children:
            right.children, full.children = full.children[t:], full.children[:t]
        parent.keys.insert(i, middle)
        parent.children.insert(i + 1, right)

    def height(self) -> int:
        node, levels = self.root, 1
        while node.children:
            node, levels = node.children[0], levels + 1
        return levels

    def __iter__(self):
        stack = [(self.root, 0)]
        while stack:
            node, i = stack.pop()
            if not node.children:
                yield from node.keys
                continue
            if i < len(node.keys) + 1:
                if i > 0:
                    yield node.keys[i - 1]
                stack.append((node, i + 1))
                stack.append((node.children[i], 0))


def height(root) -> int:
    best, stack = 0, [(root, 1)] if root else []
    while stack:
        node, depth = stack.pop()
        best = max(best, depth)
        stack.extend((c, depth + 1) for c in (node.left, node.right) if c)
    return best


def in_order(root) -> list:
    out, stack, node = [], [], root
    while stack or node:
        while node:
            stack.append(node)
            node = node.left
        node = stack.pop()
        out.append(node.key)
        node = node.right
    return out


# --- Experiments ------------------------------------------------------------------------------------


def heights() -> dict:
    rng = random.Random(0)
    out = {"sizes": [], "bst_random": [], "avl_random": [], "avl_sorted": [], "btree": [], "bst_sorted_sizes": [], "bst_sorted": []}
    for n in [100, 1_000, 10_000, 100_000, 1_000_000]:
        keys = rng.sample(range(10 * n), n)
        out["sizes"].append(n)
        out["bst_random"].append(height(BST(keys).root))
        out["avl_random"].append(height(AVL(keys).root))
        out["avl_sorted"].append(height(AVL(sorted(keys)).root))
        out["btree"].append(BTree(64, keys).height())
        print(f"n = {n:>9,}: BST random {out['bst_random'][-1]:3d}  AVL random {out['avl_random'][-1]:3d}"
              f"  AVL sorted {out['avl_sorted'][-1]:3d}  B-tree {out['btree'][-1]}  log2(n) {np.log2(n):.1f}")
    for n in [10, 100, 1_000, 3_000]:
        out["bst_sorted_sizes"].append(n)
        out["bst_sorted"].append(height(BST(range(n)).root))
    print("BST sorted heights:", dict(zip(out["bst_sorted_sizes"], out["bst_sorted"])))
    return out


def lookups(n: int = 1_000_000, probes: int = 20_000) -> dict:
    rng = random.Random(1)
    keys = rng.sample(range(10 * n), n)
    targets = rng.sample(keys, probes)
    trees = {"binary search tree, random order": BST(keys), "AVL tree": AVL(keys),
             "B-tree, up to 127 keys a node": BTree(64, keys), "B-tree, up to 7 keys a node": BTree(4, keys)}
    out = {}
    for name, tree in trees.items():
        visits = [tree.search(k)[1] for k in targets]
        best = float("inf")
        for _ in range(5):  # the fastest pass is the one least disturbed
            start = time.perf_counter()
            for k in targets:
                tree.search(k)
            best = min(best, time.perf_counter() - start)
        out[name] = {"mean_visits": float(np.mean(visits)), "max_visits": int(max(visits)),
                     "seconds_per_lookup": best / probes}
        print(f"{name:34s} nodes visited: mean {out[name]['mean_visits']:5.2f}, worst {out[name]['max_visits']:2d}"
              f"   {seconds(out[name]['seconds_per_lookup'])} a lookup in Python")
    return out


def index_depth(path: str, root: int, page_size: int) -> tuple[int, int]:
    """Levels in a SQLite index, read from the file, and the keys on its root."""
    levels, page = 0, root
    with open(path, "rb") as f:
        while True:
            f.seek((page - 1) * page_size + (100 if page == 1 else 0))
            header = f.read(12)  # the b-tree page header
            levels += 1
            if levels == 1:
                root_keys = int.from_bytes(header[3:5], "big")  # cells on the root
            if header[0] == 10:  # 10 marks a leaf page of an index
                return levels, root_keys
            page = int.from_bytes(header[8:12], "big")  # down the right-most child


def sqlite_demo(rows: int = 1_000_000) -> dict:
    """One row among a million in SQLite: a full scan, then a B-tree index."""
    folder = tempfile.mkdtemp()
    path = os.path.join(folder, "users.db")
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)")
    db.executemany("INSERT INTO users (email) VALUES (?)", ((f"user{i:07d}@example.com",) for i in range(rows)))
    db.commit()
    rng = random.Random(2)
    emails = [f"user{rng.randrange(rows):07d}@example.com" for _ in range(200)]
    query = "SELECT id FROM users WHERE email = ?"
    out = {"rows": rows, "page_size": db.execute("PRAGMA page_size").fetchone()[0]}

    def timed(n):
        start = time.perf_counter()
        for email in emails[:n]:
            db.execute(query, (email,)).fetchone()
        return (time.perf_counter() - start) / n

    out["plan_without_index"] = [r[-1] for r in db.execute("EXPLAIN QUERY PLAN " + query, (emails[0],))]
    out["seconds_without_index"] = timed(10)
    pages_before = db.execute("PRAGMA page_count").fetchone()[0]
    db.execute("CREATE INDEX users_email ON users (email)")
    out["index_pages"] = db.execute("PRAGMA page_count").fetchone()[0] - pages_before
    out["entries_per_index_page"] = rows / out["index_pages"]
    out["plan_with_index"] = [r[-1] for r in db.execute("EXPLAIN QUERY PLAN " + query, (emails[0],))]
    out["seconds_with_index"] = timed(200)
    out["table_pages"] = pages_before
    root = db.execute("SELECT rootpage FROM sqlite_master WHERE name = 'users_email'").fetchone()[0]
    db.commit()
    db.close()
    out["index_levels"], out["index_root_keys"] = index_depth(path, root, out["page_size"])
    os.remove(path)
    os.rmdir(folder)
    print(f"SQLite, {rows:,} rows, page size {out['page_size']} bytes:")
    print(f"  without an index: {out['plan_without_index']} -> {seconds(out['seconds_without_index'])} a lookup")
    print(f"  with an index:    {out['plan_with_index']} -> {seconds(out['seconds_with_index'])} a lookup")
    print(f"  table pages {out['table_pages']:,}; index pages {out['index_pages']:,}, "
          f"about {out['entries_per_index_page']:.0f} entries a page")
    print(f"  read from the file: the index is {out['index_levels']} levels deep, "
          f"with {out['index_root_keys']} keys on its root page")
    return out


def compute() -> dict:
    results = {"machine": machine(), "sqlite_version": sqlite3.sqlite_version}
    results["heights"] = heights()
    results["lookups"] = lookups()
    results["sqlite"] = sqlite_demo()
    return results


# --- Charts ------------------------------------------------------------------------------------------


def _layout(root) -> dict:
    """x from in-order position, y from depth."""
    pos, stack, node, i = {}, [], root, 0
    depth = {id(root): 0} if root else {}
    while stack or node:
        while node:
            stack.append(node)
            for c in (node.left, node.right):
                if c:
                    depth[id(c)] = depth[id(node)] + 1
            node = node.left
        node = stack.pop()
        pos[id(node)] = (i, -depth[id(node)])
        i += 1
        node = node.right
    return pos


def _draw_binary(ax, root, title, highlight=False):
    pos = _layout(root)
    stack = [root]
    while stack:
        node = stack.pop()
        for c in (node.left, node.right):
            if c:
                ax.plot(*zip(pos[id(node)], pos[id(c)]), color=MUTED, linewidth=1, zorder=1)
                stack.append(c)
    for node_id, (x, y) in pos.items():
        ax.add_patch(plt.Circle((x, y), 0.38, facecolor="#faf9f6", edgecolor=ACCENT if highlight else INK_2, linewidth=1, zorder=2))
    stack = [root]
    while stack:
        node = stack.pop()
        x, y = pos[id(node)]
        ax.text(x, y, str(node.key), ha="center", va="center", fontsize=7.5, color=INK, zorder=3)
        stack.extend(c for c in (node.left, node.right) if c)
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    ax.set_xlim(min(xs) - 0.8, max(xs) + 0.8)
    ax.set_ylim(min(ys) - 0.8, 0.8)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"{title}: height {height(root)}", fontsize=9, loc="left")


def _draw_btree(ax, tree: BTree):
    levels, frontier = [], [tree.root]
    while frontier:
        levels.append(frontier)
        frontier = [c for n in frontier for c in n.children]
    width = max(sum(len(n.keys) + 0.6 for n in level) for level in levels)
    centres = {}
    for depth, level in enumerate(levels):
        total = sum(len(n.keys) + 0.6 for n in level)
        x = (width - total) / 2
        for n in level:
            w = len(n.keys)
            for j, k in enumerate(n.keys):
                ax.add_patch(plt.Rectangle((x + j, -depth * 1.6), 1, 0.7, facecolor="#dfe5df" if depth == 0 else "#faf9f6",
                                           edgecolor=INK_2, linewidth=0.9))
                ax.text(x + j + 0.5, -depth * 1.6 + 0.35, str(k), ha="center", va="center", fontsize=7.5, color=INK)
            centres[id(n)] = (x + w / 2, -depth * 1.6)
            x += w + 0.6
    for level in levels[:-1]:
        for n in level:
            cx, cy = centres[id(n)]
            for c in n.children:
                ccx, ccy = centres[id(c)]
                ax.plot([cx, ccx], [cy, ccy + 0.7], color=MUTED, linewidth=0.9)
    ax.set_xlim(-0.5, width + 0.5)
    ax.set_ylim(-(len(levels) - 1) * 1.6 - 0.4, 1.0)
    ax.axis("off")
    ax.set_title(f"{len(list(tree))} keys in a B-tree, up to 3 a node: height {len(levels)}", fontsize=9, loc="left")


def draw_trees() -> None:
    keys = [50, 30, 70, 20, 40, 60, 80, 35, 45, 65, 10, 75, 85, 55, 25]
    fig, axes = plt.subplots(2, 2, figsize=(8.6, 6.0), gridspec_kw={"height_ratios": [1, 1.25]})
    _draw_binary(axes[0, 0], BST(keys).root, "15 keys in a mixed order")
    _draw_binary(axes[0, 1], AVL(sorted(keys)).root, "the same keys sorted, AVL", highlight=True)
    _draw_binary(axes[1, 0], BST(sorted(keys)[:7]).root, "7 keys sorted, plain BST")
    _draw_btree(axes[1, 1], BTree(2, sorted(keys) + [5, 15]))
    fig.tight_layout()
    save(fig, SLUG, "trees")


def draw_heights(results: dict) -> None:
    h = results["heights"]
    fig, ax = plt.subplots(figsize=(6.8, 3.9))
    sizes = h["sizes"]
    series = [("bst_random", "binary search tree, random order", INK_2), ("avl_random", "AVL tree", ACCENT),
              ("btree", "B-tree, up to 127 keys a node", INK)]
    for key, label, color in series:
        ax.plot(sizes, h[key], color=color, linewidth=2 if key == "avl_random" else 1.6, marker="o", markersize=4,
                markeredgecolor="white", markeredgewidth=0.8)
        ax.annotate(label, (sizes[-1], h[key][-1]), xytext=(6, 0), textcoords="offset points", fontsize=8.5, color=color, va="center")
    ax.plot(sizes, np.log2(sizes), color=MUTED, linestyle="--", linewidth=1)
    ax.annotate("log2(n)", (sizes[-1], np.log2(sizes[-1])), xytext=(6, -12), textcoords="offset points", fontsize=8, color=INK_2)
    ax.plot(h["bst_sorted_sizes"], h["bst_sorted"], color=INK_2, linestyle=":", linewidth=1.6, marker="o", markersize=3.5)
    ax.annotate("binary search tree, sorted order:\nheight = n", (h["bst_sorted_sizes"][-1], h["bst_sorted"][-1]),
                xytext=(8, 0), textcoords="offset points", fontsize=8, color=INK_2, va="center")
    ax.set_xscale("log")
    ax.set_yscale("log")
    plain_numbers(ax.xaxis)
    plain_numbers(ax.yaxis)
    ax.set_xlim(80, 1.2e7)
    ax.set_xlabel("keys in the tree (log scale)")
    ax.set_ylabel("height: nodes from root to deepest leaf")
    ax.set_title("Height decides how many steps a lookup takes", fontsize=10)
    fig.subplots_adjust(right=0.75)
    save(fig, SLUG, "heights")


if __name__ == "__main__":
    sys.setrecursionlimit(10_000)
    path = Path(__file__).parent / "results" / f"{SLUG}.json"
    if "--charts-only" in sys.argv:
        results = json.loads(path.read_text())
    else:
        results = compute()
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(results, indent=1))
        print(f"  wrote {path.name}")
    draw_trees()
    draw_heights(results)
