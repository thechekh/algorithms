"""Dijkstra finds the cheapest path, A* finds the same cost, and the shortcuts are honest about theirs."""

import math
import random

import pytest

from shortest_paths import (MAP, Grid, a_star, breadth_first, dijkstra, dijkstra_scan_all,
                            dijkstra_without_a_heap, greedy, random_grid)


def bellman_ford(grid: Grid) -> float:
    """Relax every edge until nothing changes: slow, simple, and certainly right."""
    cost = {cell: math.inf for cell in grid.cells}
    cost[grid.start] = 0
    for _ in range(len(grid.cells)):
        changed = False
        for cell in grid.cells:
            for n in grid.neighbours(cell):
                if cost[cell] + grid.cost(n) < cost[n]:
                    cost[n] = cost[cell] + grid.cost(n)
                    changed = True
        if not changed:
            break
    return cost[grid.goal]


def valid(grid: Grid, path) -> bool:
    return (path[0] == grid.start and path[-1] == grid.goal
            and all(b in grid.neighbours(a) for a, b in zip(path, path[1:])))


@pytest.mark.parametrize("seed", range(40))
def test_every_version_agrees_with_bellman_ford(seed):
    grid = Grid(random_grid(random.Random(seed), 12))
    truth = bellman_ford(grid)
    d_path, d_cost, _ = dijkstra(grid)
    assert d_cost == truth
    assert a_star(grid)[1] == truth
    assert dijkstra_without_a_heap(grid)[1] == truth
    assert dijkstra_scan_all(grid) == truth
    if d_path is not None:
        assert valid(grid, d_path) and grid.path_cost(d_path) == d_cost
        for fn in (a_star, greedy, breadth_first):
            path, cost, _ = fn(grid)
            assert valid(grid, path) and grid.path_cost(path) == cost and cost >= truth


def test_the_map_in_the_article():
    grid = Grid(MAP)
    bfs_path, bfs_cost, _ = breadth_first(grid)
    d_path, d_cost, d_order = dijkstra(grid)
    a_path, a_cost, a_order = a_star(grid)
    assert a_cost == d_cost < bfs_cost  # the fewest steps is not the cheapest route
    assert len(a_order) < len(d_order)  # the guess saves work
    assert len(bfs_path) <= len(d_path)


def test_with_equal_costs_dijkstra_is_bfs():
    grid = Grid(random_grid(random.Random(3), 15, forest=0.0))
    assert dijkstra(grid)[1] == len(breadth_first(grid)[0]) - 1


def test_unreachable_goal():
    grid = Grid(["S#.", "##.", "..G"])
    assert dijkstra(grid)[0] is None and a_star(grid)[1] == math.inf
    assert dijkstra_without_a_heap(grid)[0] is None and dijkstra_scan_all(grid) == math.inf
