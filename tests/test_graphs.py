"""BFS finds the shortest path, DFS finds a path, both know when there is none."""

import itertools
import random

import pytest

from graphs import MAZE, bfs, dfs, parse, random_maze


def shortest_by_brute_force(graph, start, goal):
    """Try every simple path; keep the shortest. Only for tiny graphs."""
    best = None
    nodes = [n for n in graph if n not in (start, goal)]
    for k in range(len(nodes) + 1):
        for middle in itertools.permutations(nodes, k):
            path = (start, *middle, goal)
            if all(b in graph[a] for a, b in zip(path, path[1:])):
                if best is None or len(path) < len(best):
                    best = list(path)
        if best is not None:
            return best
    return None


@pytest.mark.parametrize("seed", range(30))
def test_bfs_is_shortest_on_small_random_graphs(seed):
    rng = random.Random(seed)
    names = "ABCDEFG"
    graph = {n: [] for n in names}
    for a, b in itertools.combinations(names, 2):
        if rng.random() < 0.35:
            graph[a].append(b)
            graph[b].append(a)
    b_path, _ = bfs(graph, "A", "G")
    brute = shortest_by_brute_force(graph, "A", "G")
    assert (b_path is None) == (brute is None)
    if brute:
        assert len(b_path) == len(brute)


@pytest.mark.parametrize("seed", range(30))
def test_dfs_finds_a_valid_path_whenever_bfs_does(seed):
    graph, start, goal = parse(random_maze(random.Random(seed)))
    b_path, _ = bfs(graph, start, goal)
    d_path, _ = dfs(graph, start, goal)
    assert (b_path is None) == (d_path is None)
    if d_path:
        assert d_path[0] == start and d_path[-1] == goal
        assert all(b in graph[a] for a, b in zip(d_path, d_path[1:]))
        assert len(d_path) >= len(b_path)


def test_the_hand_made_maze():
    graph, start, goal = parse(MAZE)
    b_path, b_order = bfs(graph, start, goal)
    d_path, d_order = dfs(graph, start, goal)
    assert b_path[0] == start == (0, 0) and b_path[-1] == goal
    assert len(d_path) >= len(b_path)
    assert len(set(b_order)) == len(b_order)  # no cell visited twice


def test_unreachable_goal_returns_none():
    graph = {"A": ["B"], "B": ["A"], "C": []}
    assert bfs(graph, "A", "C") == (None, ["A", "B"])
    assert dfs(graph, "A", "C")[0] is None
