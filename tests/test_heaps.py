"""The heap agrees with heapq under random operations, and every top-k method agrees with sorted()."""

import heapq
import random

import pytest

from heaps import TOP_K, Counted, Heap, TracedHeap, build_comparisons


def is_heap(items) -> bool:
    return all(not items[i] < items[(i - 1) // 2] for i in range(1, len(items)))


@pytest.mark.parametrize("seed", range(30))
def test_matches_heapq_under_random_pushes_and_pops(seed):
    rng = random.Random(seed)
    ours, theirs = Heap(), []
    for _ in range(400):
        if theirs and rng.random() < 0.4:
            assert ours.pop() == heapq.heappop(theirs)
        else:
            x = rng.randint(0, 50)
            ours.push(x)
            heapq.heappush(theirs, x)
        assert is_heap(ours.items) and len(ours) == len(theirs)
        if theirs:
            assert ours.peek() == theirs[0]


@pytest.mark.parametrize("n", [0, 1, 2, 7, 64, 1000])
def test_heapify_and_heapsort(n):
    rng = random.Random(n)
    values = [rng.random() for _ in range(n)]
    heap = Heap(values)
    assert is_heap(heap.items)
    assert [heap.pop() for _ in range(n)] == sorted(values)


@pytest.mark.parametrize("n", [5, 10, 11, 500])
def test_every_top_k_method_agrees_with_sorted(n):
    rng = random.Random(n)
    data = [rng.randint(0, 100) for _ in range(n)]  # with repeats
    k = min(10, n)
    for name, fn in TOP_K.items():
        assert fn(data, k) == sorted(data, reverse=True)[:k], name


def test_the_traced_example():
    heap = TracedHeap([7, 2, 9, 4, 8, 3, 6, 5])
    assert heap.items == [2, 4, 3, 5, 8, 9, 6, 7]
    heap.push(1)
    assert len(heap.steps) == 3 and heap.items == [1, 2, 3, 4, 8, 9, 6, 7, 5]
    heap.steps.clear()
    assert heap.pop() == 1 and len(heap.steps) == 2 and heap.items == [2, 4, 3, 5, 8, 9, 6, 7]


def test_heapify_is_linear_even_when_pushing_is_not():
    rng = random.Random(1)
    values = sorted((rng.random() for _ in range(4096)), reverse=True)
    counts = build_comparisons(values)
    assert counts["heapify in one pass"] <= 2  # at most two comparisons per item
    assert counts["push one by one"] > 10  # about log2(n) per item: every push reaches the root
    Counted.comparisons = 0
