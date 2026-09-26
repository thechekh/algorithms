"""Binary search, and the off-by-one everyone writes.

Article: https://chekh.dev/writing/binary-search-and-the-off-by-one-everyone-writes/
Run:     uv run python binary_search.py    (draws the trace and the conventions diagram)
         uv run pytest tests/test_binary_search.py

Two correct binary searches — one for each convention for the search range — three
classic bugs, and a trace of every step on a short list.
"""

from collections.abc import Iterator

import matplotlib.pyplot as plt

from _common import ACCENT, INK, INK_2, MUTED, save

SLUG = "binary-search-and-the-off-by-one-everyone-writes"


def binary_search(items: list, target) -> int:
    """Index of `target` in the sorted list `items`, or -1 if it is not there.

    The range [lo, hi] is inclusive: both ends are still candidates.
    """
    lo, hi = 0, len(items) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if items[mid] == target:
            return mid
        if items[mid] < target:
            lo = mid + 1  # everything up to mid is too small
        else:
            hi = mid - 1  # everything from mid on is too big
    return -1


def bisect_left(items: list, target) -> int:
    """Leftmost index where `target` could be inserted to keep `items` sorted.

    The range [lo, hi) is half-open: hi is one past the last candidate. This is what
    the standard library's bisect.bisect_left does.
    """
    lo, hi = 0, len(items)
    while lo < hi:
        mid = (lo + hi) // 2
        if items[mid] < target:
            lo = mid + 1
        else:
            hi = mid  # mid itself is still a candidate
    return lo


# The three classic bugs. Each is guarded, so a test suite cannot hang on it: a
# correct search takes at most log2(n) + 1 steps, and these give up well past that.


def _guard(items: list) -> int:
    return 2 * len(items).bit_length() + 4


def bug_misses_the_last_one(items: list, target) -> int:
    """`while lo < hi` with an inclusive range: the loop ends with one candidate unchecked."""
    lo, hi = 0, len(items) - 1
    while lo < hi:  # should be <=
        mid = (lo + hi) // 2
        if items[mid] == target:
            return mid
        if items[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def bug_never_finishes(items: list, target) -> int:
    """`hi = mid` with an inclusive range: when the target is missing, the range stops shrinking."""
    lo, hi = 0, len(items) - 1
    for _ in range(_guard(items)):
        if lo > hi:
            return -1
        mid = (lo + hi) // 2
        if items[mid] == target:
            return mid
        if items[mid] < target:
            lo = mid + 1
        else:
            hi = mid  # should be mid - 1
    raise RuntimeError("the search did not finish: the range stopped shrinking")


def bug_reads_past_the_end(items: list, target) -> int:
    """`hi = len(items)` with an inclusive loop: mid can be an index that does not exist."""
    lo, hi = 0, len(items)  # should be len(items) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if items[mid] == target:  # IndexError when mid == len(items)
            return mid
        if items[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def trace(items: list, target) -> Iterator[tuple[int, int, int, str]]:
    """Every step of binary_search: (lo, mid, hi, what happened)."""
    lo, hi = 0, len(items) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if items[mid] == target:
            yield lo, mid, hi, f"{items[mid]} = {target}: found at index {mid}"
            return
        if items[mid] < target:
            yield lo, mid, hi, f"{items[mid]} < {target}: look right"
            lo = mid + 1
        else:
            yield lo, mid, hi, f"{items[mid]} > {target}: look left"
            hi = mid - 1
    yield lo, -1, hi, f"lo > hi: {target} is not there"


def _boxes(ax, values, row, inside, mid, width=1.0, height=0.72):
    for i, value in enumerate(values):
        if i == mid:
            face, edge, ink = ACCENT, ACCENT, "white"
        elif inside(i):
            face, edge, ink = "#faf9f6", MUTED, INK
        else:
            face, edge, ink = "none", "#e4e4da", "#b8b8ac"
        ax.add_patch(plt.Rectangle((i * width, row), width, height, facecolor=face, edgecolor=edge, linewidth=1))
        ax.text(i * width + width / 2, row + height / 2, str(value), ha="center", va="center", fontsize=9, color=ink)


def draw_trace(items: list, target) -> None:
    steps = list(trace(items, target))
    n, gap = len(items), 1.35
    fig, ax = plt.subplots(figsize=(8.0, 0.55 + 0.95 * len(steps)))
    for s, (lo, mid, hi, note) in enumerate(steps):
        row = -(s * gap)
        _boxes(ax, items, row, lambda i, lo=lo, hi=hi: lo <= i <= hi, mid)
        ax.text(-0.3, row + 0.36, f"step {s + 1}", ha="right", va="center", fontsize=9, color=INK_2)
        ax.text(n + 0.3, row + 0.36, note, ha="left", va="center", fontsize=9, color=ACCENT if "found" in note else INK)
        # One label per index: markers that land on the same box are joined with "=".
        markers: dict[int, list[str]] = {}
        for label, index in (("lo", lo), ("mid", mid), ("hi", hi)):
            if index >= 0:
                markers.setdefault(index, []).append(label)
        for index, labels in markers.items():
            ax.text(index + 0.5, row - 0.12, " = ".join(labels), ha="center", va="top", fontsize=8, color=ACCENT if "mid" in labels else INK_2)
    for i in range(n):
        ax.text(i + 0.5, 0.95, str(i), ha="center", va="bottom", fontsize=8, color=INK_2)
    ax.text(n / 2, 1.45, f"index, and the value at it — searching for {target}", ha="center", va="bottom", fontsize=9.5, color=INK)
    ax.set_xlim(-1.8, n + 7.5)
    ax.set_ylim(-(len(steps) - 1) * gap - 0.6, 1.9)
    ax.axis("off")
    save(fig, SLUG, "trace")


def draw_conventions() -> None:
    values = [3, 8, 12, 20, 27, 41, 55]
    n = len(values)
    fig, ax = plt.subplots(figsize=(7.0, 2.9))
    rows = [
        (0, "inclusive: [lo, hi]", "lo = 0, hi = len − 1 = 6 · loop while lo <= hi · hi = mid − 1", n - 1),
        (-1.9, "half-open: [lo, hi)", "lo = 0, hi = len = 7 · loop while lo < hi · hi = mid", n),
    ]
    for row, title, rule, hi in rows:
        _boxes(ax, values, row, lambda i: True, -1)
        ax.add_patch(plt.Rectangle((n, row), 1, 0.72, facecolor="none", edgecolor="#e4e4da", linewidth=1, linestyle=(0, (2, 2))))
        ax.text(n + 0.5, row + 0.36, "end", ha="center", va="center", fontsize=8, color="#b8b8ac")
        ax.text(0.5, row - 0.12, "lo", ha="center", va="top", fontsize=8.5, color=ACCENT)
        ax.text(hi + 0.5, row - 0.12, "hi", ha="center", va="top", fontsize=8.5, color=ACCENT)
        ax.text(-0.3, row + 0.5, title, ha="right", va="center", fontsize=9.5, color=INK)
        ax.text(-0.3, row + 0.18, rule, ha="right", va="center", fontsize=7.5, color=INK_2)
    ax.set_xlim(-8.2, n + 1.3)
    ax.set_ylim(-2.6, 1.0)
    ax.axis("off")
    save(fig, SLUG, "conventions")


if __name__ == "__main__":
    draw_trace([2, 5, 8, 12, 16, 23, 38, 56, 72, 91, 97, 105, 110, 120, 131], 97)
    draw_conventions()
