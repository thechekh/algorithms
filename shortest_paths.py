"""Dijkstra and A*, traced on a weighted grid.

Article: https://chekh.dev/writing/dijkstra-and-a-star-traced-on-a-weighted-grid/
Run:     uv run python shortest_paths.py                (about a minute)
         uv run python shortest_paths.py --charts-only  (redraw from results/)
         uv run pytest tests/test_shortest_paths.py

A map where forest costs five times as much to cross as open ground. BFS, Dijkstra,
A* and greedy best-first search are traced on it, run on 200 random maps, and
Dijkstra is timed with its priority queue and without one.
"""

import heapq
import json
import math
import random
import sys
import time
from itertools import count
from pathlib import Path

import matplotlib.pyplot as plt

from _common import ACCENT, INK, INK_2, MUTED, machine, plain_numbers, save, seconds, time_axis
from graphs import bfs, path_to

SLUG = "dijkstra-and-a-star-traced-on-a-weighted-grid"

MAP = """
.........ffffffff.........
.........ffffffff.........
.........ffffffff.........
....#....ffffffff....#....
....#....ffffffff....#....
....#....ffffffff....#....
S...#....ffffffff....#...G
....#....ffffffff....#....
.........ffffffff.........
.........ffffffff.........
.........ffffffff.........
..........................
..........................
""".strip().split("\n")


class Grid:
    """A map: '.' costs 1 to enter, 'f' (forest) costs 5, '#' cannot be entered."""

    COSTS = {".": 1, "f": 5, "S": 1, "G": 1}

    def __init__(self, rows: list[str]):
        self.rows = rows
        self.cells = {(r, c): self.COSTS[ch] for r, row in enumerate(rows)
                      for c, ch in enumerate(row) if ch != "#"}
        self.start = next((r, c) for r, row in enumerate(rows) for c, ch in enumerate(row) if ch == "S")
        self.goal = next((r, c) for r, row in enumerate(rows) for c, ch in enumerate(row) if ch == "G")
        self.min_cost = min(self.cells.values())

    def neighbours(self, cell):
        r, c = cell
        return [n for n in ((r - 1, c), (r, c + 1), (r + 1, c), (r, c - 1)) if n in self.cells]

    def cost(self, cell) -> int:
        return self.cells[cell]

    def path_cost(self, path) -> int:
        return sum(self.cost(cell) for cell in path[1:])


def search(grid: Grid, priority):
    """Expand whichever frontier cell `priority` ranks lowest, until the goal."""
    start, goal = grid.start, grid.goal
    g = {start: 0}  # the cheapest known cost of reaching each cell
    parent = {start: None}
    frontier = [(priority(0, start), 0, start)]
    tie = count(1)  # equal priorities leave in the order they arrived
    done, order = set(), []
    while frontier:
        _, _, cell = heapq.heappop(frontier)
        if cell in done:
            continue  # an old entry for a cell already expanded more cheaply
        done.add(cell)
        order.append(cell)
        if cell == goal:
            return path_to(parent, goal), g[goal], order
        for n in grid.neighbours(cell):
            new = g[cell] + grid.cost(n)
            if n not in done and new < g.get(n, math.inf):
                g[n], parent[n] = new, cell
                heapq.heappush(frontier, (priority(new, n), next(tie), n))
    return None, math.inf, order


def manhattan(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def dijkstra(grid: Grid):
    """Cost so far only: the cheapest frontier cell goes next."""
    return search(grid, lambda g, cell: g)


def a_star(grid: Grid):
    """Cost so far plus a guess of the cost to go, one that never overestimates."""

    def guess(cell) -> int:  # every step costs at least min_cost
        return grid.min_cost * manhattan(cell, grid.goal)

    return search(grid, lambda g, cell: g + guess(cell))


def greedy(grid: Grid):
    """The guess alone: head for the goal and ignore what the route has cost."""
    return search(grid, lambda g, cell: manhattan(cell, grid.goal))


def breadth_first(grid: Grid):
    """BFS from the graphs article: fewest steps, blind to what each step costs."""
    graph = {cell: grid.neighbours(cell) for cell in grid.cells}
    path, order = bfs(graph, grid.start, grid.goal)
    return path, (grid.path_cost(path) if path else math.inf), order


def dijkstra_without_a_heap(grid: Grid):
    """No priority queue: scan the open cells for the cheapest one, every time."""
    cost = {grid.start: 0}
    parent = {grid.start: None}
    open_cells, done = {grid.start}, set()
    while open_cells:
        cell = min(open_cells, key=cost.__getitem__)  # O(open cells) every time
        open_cells.remove(cell)
        done.add(cell)
        if cell == grid.goal:
            return path_to(parent, cell), cost[cell], len(done)
        for n in grid.neighbours(cell):
            new = cost[cell] + grid.cost(n)
            if n not in done and new < cost.get(n, math.inf):
                cost[n], parent[n] = new, cell
                open_cells.add(n)
    return None, math.inf, len(done)


def dijkstra_scan_all(grid: Grid):
    """Older still: a cost for every cell, all of them scanned each time: O(V^2)."""
    cost = {cell: math.inf for cell in grid.cells}
    cost[grid.start] = 0
    remaining = set(grid.cells)
    while remaining:
        cell = min(remaining, key=cost.__getitem__)
        if cost[cell] == math.inf or cell == grid.goal:
            return cost[cell]
        remaining.remove(cell)
        for n in grid.neighbours(cell):
            cost[n] = min(cost[n], cost[cell] + grid.cost(n))
    return math.inf


ALGORITHMS = {"BFS": breadth_first, "Dijkstra": dijkstra, "A*": a_star, "greedy best-first": greedy}


def random_grid(rng: random.Random, size: int, forest: float = 0.25, walls: float = 0.15) -> list[str]:
    rows = []
    for _ in range(size):
        rows.append("".join("#" if (x := rng.random()) < walls else ("f" if x < walls + forest else ".") for _ in range(size)))
    rows[0] = "S" + rows[0][1:]
    rows[-1] = rows[-1][:-1] + "G"
    return rows


def compute() -> dict:
    grid = Grid(MAP)
    results: dict = {"machine": machine(), "map": MAP, "traces": {}}
    for name, fn in ALGORITHMS.items():
        path, cost, order = fn(grid)
        results["traces"][name] = {"path": path, "cost": cost, "order": order}
        print(f"{name:18s} cost {cost:3d}   steps {len(path) - 1:2d}   cells expanded {len(order):3d} of {len(grid.cells)}")

    # 200 random maps: expanded cells and path cost, relative to Dijkstra
    rng = random.Random(0)
    runs = {name: {"expanded": [], "cost": []} for name in ALGORITHMS}
    solved = 0
    while solved < 200:
        g = Grid(random_grid(rng, 30))
        if dijkstra(g)[0] is None:
            continue
        solved += 1
        for name, fn in ALGORITHMS.items():
            path, cost, order = fn(g)
            runs[name]["expanded"].append(len(order))
            runs[name]["cost"].append(cost)
    base_cost, base_expanded = runs["Dijkstra"]["cost"], runs["Dijkstra"]["expanded"]
    results["random"] = {}
    for name, run in runs.items():
        cost_ratio = [c / b for c, b in zip(run["cost"], base_cost)]
        expanded_ratio = [e / b for e, b in zip(run["expanded"], base_expanded)]
        results["random"][name] = {
            "cost_ratio": cost_ratio, "expanded_ratio": expanded_ratio,
            "mean_cost_ratio": sum(cost_ratio) / solved, "mean_expanded_ratio": sum(expanded_ratio) / solved,
            "optimal_share": sum(1 for r in cost_ratio if r == 1) / solved,
            "worst_cost_ratio": max(cost_ratio), "mean_expanded": sum(run["expanded"]) / solved,
        }
        r = results["random"][name]
        print(f"{name:18s} optimal in {r['optimal_share']:4.0%}   mean cost {r['mean_cost_ratio']:.2f}x   worst {r['worst_cost_ratio']:.2f}x"
              f"   cells expanded {r['mean_expanded']:5.0f} ({r['mean_expanded_ratio']:.0%} of Dijkstra's)")

    # With a heap and without: time to cross an open n-by-n map from corner to corner
    results["timing"] = {"cells": [], "heap": [], "scan open cells": [], "scan all cells": []}
    for n in [10, 20, 30, 45, 60, 90, 135, 200]:
        g = Grid(random_grid(random.Random(n), n, forest=0.3, walls=0.0))
        results["timing"]["cells"].append(n * n)
        for name, fn in [("heap", dijkstra), ("scan open cells", dijkstra_without_a_heap), ("scan all cells", dijkstra_scan_all)]:
            if name == "scan all cells" and n > 60 or name == "scan open cells" and n > 135:
                results["timing"][name].append(None)  # too slow to be worth waiting for
                continue
            best = math.inf
            for _ in range(3 if n <= 45 else 1):
                start = time.perf_counter()
                fn(g)
                best = min(best, time.perf_counter() - start)
            results["timing"][name].append(best)
        print(f"{n * n:6,d} cells   " + "   ".join(f"{k} {seconds(v[-1]) if v[-1] else '-':>7}" for k, v in results["timing"].items() if k != "cells"))
    return results


# --- Charts ---------------------------------------------------------------------------------

TERRAIN = {".": "#faf9f6", "f": "#c9d3c4", "S": "#faf9f6", "G": "#faf9f6", "#": INK_2}


def draw_traces(results: dict) -> None:
    rows = results["map"]
    fig, axes = plt.subplots(2, 2, figsize=(8.4, 5.2))
    for ax, name in zip(axes.flat, ALGORITHMS):
        trace = results["traces"][name]
        expanded = {tuple(c) for c in trace["order"]}
        path = {tuple(c) for c in trace["path"]}
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                ax.add_patch(plt.Rectangle((c, -r - 1), 1, 1, facecolor=TERRAIN[ch], edgecolor="white", linewidth=0.6))
                if (r, c) in path:
                    ax.add_patch(plt.Rectangle((c + 0.18, -r - 0.82), 0.64, 0.64, facecolor=ACCENT, edgecolor="none"))
                elif (r, c) in expanded:
                    ax.plot(c + 0.5, -r - 0.5, marker="o", markersize=2.6, color=INK, linestyle="none")
                if ch in "SG":
                    ax.text(c + 0.5, -r - 0.5, ch, ha="center", va="center", fontsize=7, color="white", fontweight="semibold")
        ax.set_xlim(0, len(rows[0]))
        ax.set_ylim(-len(rows), 0)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"{name}: cost {trace['cost']}, {len(trace['order'])} cells expanded", fontsize=9.5, loc="left")
    fig.text(0.01, 0.005, "light cells cost 1, shaded forest costs 5, dark cells are walls; dots are cells expanded, green squares the path",
             fontsize=8, color=INK_2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    save(fig, SLUG, "traces")


def draw_random(results: dict) -> None:
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    colors = {"BFS": INK_2, "Dijkstra": INK, "A*": ACCENT, "greedy best-first": MUTED}
    rng = random.Random(1)
    for name, run in results["random"].items():
        xs = [e * rng.uniform(0.985, 1.015) for e in run["expanded_ratio"]]
        ys = [c * rng.uniform(0.997, 1.003) for c in run["cost_ratio"]]
        ax.scatter(xs, ys, s=9, color=colors[name], alpha=0.5, linewidths=0)
        ax.plot(run["mean_expanded_ratio"], run["mean_cost_ratio"], marker="o", markersize=8, color=colors[name], markeredgecolor="white")
        ax.annotate(name, (run["mean_expanded_ratio"], run["mean_cost_ratio"]), xytext=(10, 8), textcoords="offset points", fontsize=8.5, color=colors[name],
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 1.5})
    ax.set_xlabel("cells expanded, as a share of Dijkstra's")
    ax.set_ylabel("path cost, as a multiple of the cheapest")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("200 random 30-by-30 maps: work against quality")
    save(fig, SLUG, "random")


def draw_timing(results: dict) -> None:
    t = results["timing"]
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    for name, color in [("heap", ACCENT), ("scan open cells", INK), ("scan all cells", INK_2)]:
        pairs = [(c, v) for c, v in zip(t["cells"], t[name]) if v]
        ax.plot(*zip(*pairs), color=color, linewidth=2 if name == "heap" else 1.6, marker="o", markersize=3.5, markeredgecolor="white", markeredgewidth=0.8)
        label = {"heap": "with a heap", "scan open cells": "scan the frontier", "scan all cells": "scan every cell"}[name]
        ax.annotate(label, pairs[-1], xytext=(6, 0), textcoords="offset points", ha="left", va="center", fontsize=8.5, color=color)
    ax.set_xlim(70, 250_000)
    ax.set_xscale("log")
    ax.set_yscale("log")
    plain_numbers(ax.xaxis)
    time_axis(ax.yaxis)
    ax.set_xlabel("cells in the map (log scale)")
    ax.set_ylabel("time to find the path (log scale)")
    ax.set_title("What the priority queue buys")
    save(fig, SLUG, "timing")


if __name__ == "__main__":
    path = Path(__file__).parent / "results" / f"{SLUG}.json"
    if "--charts-only" in sys.argv:
        results = json.loads(path.read_text())
    else:
        results = compute()
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(results))
        print(f"  wrote {path.name}")
    draw_traces(results)
    draw_random(results)
    draw_timing(results)
