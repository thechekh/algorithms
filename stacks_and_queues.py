"""Stacks, queues and the call stack.

Article: https://chekh.dev/writing/stacks-and-queues-and-the-call-stack/
Run:     uv run python stacks_and_queues.py                (about a minute)
         uv run python stacks_and_queues.py --charts-only  (redraw from results/)
         uv run pytest tests/test_stacks_and_queues.py

A stack checks brackets and evaluates arithmetic; four queues are timed as they grow;
and a nested structure 100,000 levels deep is walked twice, once by recursion, which
Python stops, and once with an explicit stack, which it does not.
"""

import json
import operator
import queue
import re
import sys
import time
from collections import deque
from pathlib import Path

import matplotlib.pyplot as plt

from _common import ACCENT, DANGER, INK, INK_2, MUTED, machine, plain_numbers, save, seconds, time_axis

SLUG = "stacks-and-queues-and-the-call-stack"
PAIRS = {")": "(", "]": "[", "}": "{"}


def balanced(text: str, trace: list | None = None) -> bool:
    """Every closing bracket must match the most recent unmatched opening one."""
    stack = []
    for ch in text:
        if ch in "([{":
            stack.append(ch)  # push: remember it until its partner arrives
        elif ch in PAIRS:
            if not stack or stack.pop() != PAIRS[ch]:  # pop: must match the latest
                return False
        if trace is not None:
            trace.append((ch, "".join(stack)))
    return not stack  # anything left open is an error too


PRECEDENCE = {"+": 1, "-": 1, "*": 2, "/": 2}
APPLY = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv}
TOKEN = re.compile(r"\d+(?:\.\d+)?|[-+*/()]")


def to_postfix(expression: str) -> list[str]:
    """Dijkstra's shunting-yard: operators wait on a stack until a weaker one arrives."""
    output, ops = [], []
    for token in TOKEN.findall(expression):
        if token in PRECEDENCE:
            while ops and ops[-1] != "(" and PRECEDENCE[ops[-1]] >= PRECEDENCE[token]:
                output.append(ops.pop())
            ops.append(token)
        elif token == "(":
            ops.append(token)
        elif token == ")":
            while ops[-1] != "(":
                output.append(ops.pop())
            ops.pop()
        else:
            output.append(token)
    return output + ops[::-1]


def evaluate_postfix(tokens: list[str], trace: list | None = None) -> float:
    stack = []
    for token in tokens:
        if token in APPLY:
            right, left = stack.pop(), stack.pop()
            stack.append(APPLY[token](left, right))
        else:
            stack.append(float(token))
        if trace is not None:
            trace.append((token, list(stack)))
    return stack.pop()


class TwoStackQueue:
    """A queue from two stacks: push onto one, pop from the other."""

    def __init__(self):
        self.inbox, self.outbox = [], []

    def put(self, item) -> None:
        self.inbox.append(item)

    def get(self):
        if not self.outbox:
            while self.inbox:  # each item is moved once: O(1) on average
                self.outbox.append(self.inbox.pop())
        return self.outbox.pop()


def nested(depth: int) -> list:
    """[1, [2, [3, ... ]]]: a structure as deep as you like."""
    root = current = []
    for i in range(1, depth + 1):
        inner = []
        current.extend([i, inner])
        current = inner
    return root


def total_recursive(items: list) -> int:
    return sum(total_recursive(x) if isinstance(x, list) else x for x in items)


def total_with_a_stack(items: list) -> int:
    total, stack = 0, [items]
    while stack:
        for x in stack.pop():
            if isinstance(x, list):
                stack.append(x)  # visit it later, instead of recursing now
            else:
                total += x
    return total


def queue_timings(sizes: list[int]) -> dict:
    """Put n items in, then take them all out, per item."""

    def run_list(n):
        q = []
        for i in range(n):
            q.append(i)
        while q:
            q.pop(0)  # every item after the first shifts one place left

    def run_deque(n):
        q = deque()
        for i in range(n):
            q.append(i)
        while q:
            q.popleft()

    def run_two_stacks(n):
        q = TwoStackQueue()
        for i in range(n):
            q.put(i)
        for _ in range(n):
            q.get()

    def run_queue(n):
        q = queue.Queue()
        for i in range(n):
            q.put(i)
        for _ in range(n):
            q.get()

    impls = {"list.pop(0)": run_list, "collections.deque": run_deque, "two stacks": run_two_stacks, "queue.Queue": run_queue}
    out = {name: [] for name in impls}
    for n in sizes:
        for name, run in impls.items():
            if name == "list.pop(0)" and n > 300_000:
                out[name].append(None)
                continue
            best = min(_timed(lambda: run(n)) for _ in range(3 if n <= 100_000 else 1))
            out[name].append(best / n)
        print(f"n = {n:>9,}  " + "  ".join(f"{k}: {seconds(v[-1]) if v[-1] else '-':>7}/item" for k, v in out.items()))
    return out


def _timed(fn) -> float:
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


def compute() -> dict:
    results: dict = {"machine": machine()}
    trace: list = []
    ok = balanced("{[()()]}(", trace)
    results["brackets"] = {"text": "{[()()]}(", "balanced": ok, "trace": trace}
    print("brackets:", "".join(ch for ch, _ in trace), "->", ok, [s for _, s in trace])

    expression = "3 + 4 * (2 - 1)"
    postfix = to_postfix(expression)
    steps: list = []
    value = evaluate_postfix(postfix, steps)
    results["postfix"] = {"expression": expression, "postfix": postfix, "value": value, "trace": steps}
    print(f"{expression} -> {' '.join(postfix)} = {value}")

    sizes = [1_000, 10_000, 100_000, 300_000, 1_000_000]
    results["queue_sizes"] = sizes
    results["queues"] = queue_timings(sizes)

    depth = 100_000
    deep = nested(depth)
    results["depth"] = {"depth": depth, "recursion_limit": sys.getrecursionlimit()}
    try:
        total_recursive(deep)
        results["depth"]["recursive"] = "finished"
    except RecursionError as e:
        results["depth"]["recursive"] = f"RecursionError: {e}"
    start = time.perf_counter()
    results["depth"]["with_a_stack"] = total_with_a_stack(deep)
    results["depth"]["with_a_stack_seconds"] = time.perf_counter() - start
    print(f"depth {depth:,}: recursive -> {results['depth']['recursive']}; with a stack -> "
          f"{results['depth']['with_a_stack']:,} in {seconds(results['depth']['with_a_stack_seconds'])}")
    return results


# --- Charts -------------------------------------------------------------------------------


def draw_trace(results: dict) -> None:
    trace = results["brackets"]["trace"]
    fig, ax = plt.subplots(figsize=(8.2, 3.0))
    ax.set_xlim(-0.6, len(trace) + 0.2)
    ax.set_ylim(-1.0, 3.2)
    ax.axis("off")
    for col, (ch, stack) in enumerate(trace):
        pushed = ch in "([{"
        ax.text(col + 0.4, 2.85, ch, ha="center", va="center", fontsize=13, color=ACCENT if pushed else INK, fontweight="semibold")
        ax.text(col + 0.4, 2.4, "push" if pushed else "pop", ha="center", va="center", fontsize=7.5, color=INK_2)
        for depth, item in enumerate(stack):
            top = depth == len(stack) - 1
            ax.add_patch(plt.Rectangle((col + 0.1, depth * 0.62), 0.6, 0.55, facecolor=ACCENT if top else "#faf9f6",
                                       edgecolor=INK_2, linewidth=0.9))
            ax.text(col + 0.4, depth * 0.62 + 0.27, item, ha="center", va="center", fontsize=10, color="white" if top else INK)
        ax.plot([col + 0.05, col + 0.75], [-0.05, -0.05], color=MUTED, linewidth=1)
    ax.text(-0.5, -0.55, "the stack after each character, top in green", fontsize=8, color=INK_2, va="top")
    ax.text(len(trace) - 0.6, 1.1, "one '(' left:\nnot balanced", fontsize=8, color=DANGER, ha="center", va="bottom")
    save(fig, SLUG, "trace")


def draw_queues(results: dict) -> None:
    sizes = results["queue_sizes"]
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    colors = {"list.pop(0)": INK_2, "collections.deque": ACCENT, "two stacks": INK, "queue.Queue": MUTED}
    for name, times in results["queues"].items():
        pairs = [(n, t) for n, t in zip(sizes, times) if t]
        ax.plot(*zip(*pairs), color=colors[name], linewidth=2 if name == "collections.deque" else 1.6, marker="o",
                markersize=3.5, markeredgecolor="white", markeredgewidth=0.8)
        ax.annotate(name, pairs[-1], xytext=(6, 0), textcoords="offset points", fontsize=8.5, color=colors[name], va="center")
    ax.set_xscale("log")
    ax.set_yscale("log")
    plain_numbers(ax.xaxis)
    time_axis(ax.yaxis)
    ax.set_xlim(800, 4e6)
    ax.set_xlabel("items put in, then taken out (log scale)")
    ax.set_ylabel("time per item (log scale)")
    ax.set_title("Four queues: only one gets slower per item as it grows", fontsize=10)
    fig.subplots_adjust(right=0.78)
    save(fig, SLUG, "queues")


if __name__ == "__main__":
    path = Path(__file__).parent / "results" / f"{SLUG}.json"
    if "--charts-only" in sys.argv:
        results = json.loads(path.read_text())
    else:
        results = compute()
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(results, indent=1))
        print(f"  wrote {path.name}")
    draw_trace(results)
    draw_queues(results)
