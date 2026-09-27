"""Graphs: BFS and DFS, traced step by step.

Article: https://chekh.dev/writing/graphs-bfs-and-dfs-traced-step-by-step/
Run:     uv run python graphs.py                 (about ten seconds)
         uv run python graphs.py --charts-only   (redraw from results/)
         uv run pytest tests/test_graphs.py

A maze as a graph, breadth-first and depth-first search traced cell by cell on it,
and both run on 300 random mazes to compare the paths they find.
"""

import json
import random
import sys
from collections import deque
from pathlib import Path

import matplotlib.pyplot as plt

from _common import ACCENT, INK, INK_2, MUTED, save

SLUG = "graphs-bfs-and-dfs-traced-step-by-step"

MAZE = """
S........#
.#######.#
.#.......#
.#.#######
.#........
.########.
.########.
.########.
.........G
""".strip().split("\n")


def parse(rows: list[str]):
    """The maze as a graph: every open cell is a node, joined to its open
    neighbours."""
    cells = {}
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch != "#":
                cells[(r, c)] = ch
    start = next(cell for cell, ch in cells.items() if ch == "S")
    goal = next(cell for cell, ch in cells.items() if ch == "G")
    graph = {cell: [n for n in neighbours(cell) if n in cells] for cell in cells}
    return graph, start, goal


def neighbours(cell):
    r, c = cell
    return [(r - 1, c), (r, c + 1), (r + 1, c), (r, c - 1)]  # up, right, down, left


def bfs(graph: dict, start, goal):
    """Breadth-first: a queue. Everything one step away, then two, then three."""
    queue = deque([start])
    parent = {start: None}
    order = []
    while queue:
        cell = queue.popleft()
        order.append(cell)
        if cell == goal:
            return path_to(parent, goal), order
        for n in graph[cell]:
            if n not in parent:
                parent[n] = cell
                queue.append(n)
    return None, order


def dfs(graph: dict, start, goal):
    """Depth-first: a stack. Follow one route as far as it goes, then back up."""
    stack = [start]
    parent = {start: None}
    order = []
    while stack:
        cell = stack.pop()
        order.append(cell)
        if cell == goal:
            return path_to(parent, goal), order
        for n in reversed(graph[cell]):  # so "up" is popped first, like bfs
            if n not in parent:
                parent[n] = cell
                stack.append(n)
    return None, order


def path_to(parent: dict, goal) -> list:
    path, cell = [], goal
    while cell is not None:
        path.append(cell)
        cell = parent[cell]
    return path[::-1]


def random_maze(rng: random.Random, size: int = 15, walls: float = 0.3) -> list[str]:
    rows = [["#" if rng.random() < walls else "." for _ in range(size)] for _ in range(size)]
    rows[0][0], rows[-1][-1] = "S", "G"
    return ["".join(row) for row in rows]


def compute() -> dict:
    graph, start, goal = parse(MAZE)
    results: dict = {"maze": MAZE, "traces": {}}
    for name, search in [("BFS", bfs), ("DFS", dfs)]:
        path, order = search(graph, start, goal)
        results["traces"][name] = {"path": path, "order": order}
        print(f"{name}: path of {len(path) - 1} steps, {len(order)} cells visited")

    # Three hundred random mazes: how do the two compare when the maze is not hand-made?
    rng = random.Random(0)
    bfs_lengths, dfs_lengths, bfs_visited, dfs_visited, solvable = [], [], [], [], 0
    tries = 0
    while solvable < 300:
        tries += 1
        graph, start, goal = parse(random_maze(rng))
        b_path, b_order = bfs(graph, start, goal)
        if b_path is None:
            continue
        solvable += 1
        d_path, d_order = dfs(graph, start, goal)
        bfs_lengths.append(len(b_path) - 1)
        dfs_lengths.append(len(d_path) - 1)
        bfs_visited.append(len(b_order))
        dfs_visited.append(len(d_order))
    ratio = [d / b for b, d in zip(bfs_lengths, dfs_lengths)]
    results["random"] = {
        "mazes": solvable, "tried": tries,
        "bfs_mean_length": sum(bfs_lengths) / solvable, "dfs_mean_length": sum(dfs_lengths) / solvable,
        "dfs_longer_share": sum(1 for r in ratio if r > 1) / solvable, "worst_ratio": max(ratio),
        "bfs_mean_visited": sum(bfs_visited) / solvable, "dfs_mean_visited": sum(dfs_visited) / solvable,
        "dfs_lengths": dfs_lengths, "bfs_lengths": bfs_lengths,
    }
    r = results["random"]
    print(f"{solvable} solvable mazes of {tries}: BFS path {r['bfs_mean_length']:.1f} steps on average, DFS {r['dfs_mean_length']:.1f}; "
          f"DFS longer in {r['dfs_longer_share']:.0%}, worst {r['worst_ratio']:.1f}x; cells visited: BFS {r['bfs_mean_visited']:.0f}, DFS {r['dfs_mean_visited']:.0f}")
    return results


def draw_maze(results: dict) -> None:
    rows = results["maze"]
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 4.3))
    for ax, name in zip(axes, ["BFS", "DFS"]):
        trace = results["traces"][name]
        order = {tuple(c): i for i, c in enumerate(trace["order"])}
        path = {tuple(c) for c in trace["path"]}
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch == "#":
                    ax.add_patch(plt.Rectangle((c, -r - 1), 1, 1, facecolor=INK_2, edgecolor="white", linewidth=0.8))
                    continue
                visited = (r, c) in order
                face = ACCENT if (r, c) in path else ("#dfe5df" if visited else "#faf9f6")
                ax.add_patch(plt.Rectangle((c, -r - 1), 1, 1, facecolor=face, edgecolor="white", linewidth=0.8))
                label = "S" if ch == "S" else "G" if ch == "G" else (str(order[(r, c)]) if visited else "")
                ax.text(c + 0.5, -r - 0.5, label, ha="center", va="center", fontsize=6.5 if label not in ("S", "G") else 8.5, color="white" if (r, c) in path else INK_2, fontweight="semibold" if label in ("S", "G") else "normal")
        ax.set_xlim(0, len(rows[0]))
        ax.set_ylim(-len(rows), 0)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"{name}: {len(trace['path']) - 1} steps, {len(trace['order'])} cells visited", fontsize=10.5, loc="left")
    fig.tight_layout()
    save(fig, SLUG, "maze")


def draw_graph() -> None:
    """A six-node graph with its adjacency list and both visiting orders."""
    pos = {"A": (0, 1), "B": (1, 2), "C": (1, 0), "D": (2, 2), "E": (2, 0), "F": (3, 1)}
    graph = {"A": ["B", "C"], "B": ["A", "D"], "C": ["A", "E"], "D": ["B", "F"], "E": ["C", "F"], "F": ["D", "E"]}
    fig, ax = plt.subplots(figsize=(7.6, 3.0))
    ax.set_xlim(-0.5, 7.4)
    ax.set_ylim(-0.6, 2.6)
    ax.axis("off")
    drawn = set()
    for a, bs in graph.items():
        for b in bs:
            if (b, a) not in drawn:
                ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color=MUTED, linewidth=1.2, zorder=1)
                drawn.add((a, b))
    for node, (x, y) in pos.items():
        ax.add_patch(plt.Circle((x, y), 0.22, facecolor="#faf9f6", edgecolor=INK, linewidth=1.2, zorder=2))
        ax.text(x, y, node, ha="center", va="center", fontsize=9.5, color=INK, zorder=3)
    b_path, b_order = bfs(graph, "A", "F")
    d_path, d_order = dfs(graph, "A", "F")
    lines = ["graph = {"] + [f'    "{k}": {v},' for k, v in graph.items()] + ["}"]
    ax.text(3.9, 2.45, "\n".join(lines), fontsize=7.5, color=INK, family="monospace", va="top", linespacing=1.25)
    ax.text(3.9, -0.05, f"BFS from A visits {' '.join(b_order)}   path {'-'.join(b_path)}\nDFS from A visits {' '.join(d_order)}   path {'-'.join(d_path)}", fontsize=8, color=INK_2, va="top", linespacing=1.4)
    save(fig, SLUG, "graph")


def draw_lengths(results: dict) -> None:
    r = results["random"]
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    low = min(r["bfs_lengths"]) - 2
    top = max(r["dfs_lengths"]) + 2
    bins = range(low, top + 1, 2)
    ax.hist(r["dfs_lengths"], bins=bins, color=MUTED, label="DFS")
    ax.hist(r["bfs_lengths"], bins=bins, color=ACCENT, alpha=0.85, label="BFS")
    ax.legend(frameon=False, fontsize=9)
    ax.set_xlabel("length of the path found, in steps")
    ax.set_ylabel("mazes")
    ax.set_title(f"{r['mazes']} random mazes: BFS finds the shortest path, DFS finds a path", fontsize=10.5)
    save(fig, SLUG, "lengths")


if __name__ == "__main__":
    path = Path(__file__).parent / "results" / f"{SLUG}.json"
    if "--charts-only" in sys.argv:
        results = json.loads(path.read_text())
    else:
        results = compute()
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(results))
        print(f"  wrote {path.name}")
    draw_graph()
    draw_maze(results)
    draw_lengths(results)
