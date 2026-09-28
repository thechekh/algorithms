"""The stack-based tools agree with Python, and the explicit stack goes deeper than recursion."""

import random
from collections import deque

import pytest

from stacks_and_queues import (TwoStackQueue, balanced, evaluate_postfix, nested, to_postfix, total_recursive,
                               total_with_a_stack)


@pytest.mark.parametrize("text, expected", [("", True), ("()", True), ("{[()()]}", True), ("{[()()]}(", False),
                                            ("(]", False), ("([)]", False), ("))", False), ("a(b[c]{d}e)f", True)])
def test_balanced(text, expected):
    assert balanced(text) is expected


@pytest.mark.parametrize("seed", range(40))
def test_shunting_yard_agrees_with_python(seed):
    rng = random.Random(seed)

    def expr(depth):
        if depth == 0 or rng.random() < 0.3:
            return str(rng.randint(1, 9))
        text = f"{expr(depth - 1)} {rng.choice('+-*')} {expr(depth - 1)}"
        return f"({text})" if rng.random() < 0.4 else text

    e = expr(4)
    assert evaluate_postfix(to_postfix(e)) == pytest.approx(eval(e))


def test_the_worked_example():
    assert to_postfix("3 + 4 * (2 - 1)") == ["3", "4", "2", "1", "-", "*", "+"]
    assert evaluate_postfix(to_postfix("3 + 4 * (2 - 1)")) == 7


@pytest.mark.parametrize("seed", range(10))
def test_two_stack_queue_is_first_in_first_out(seed):
    rng = random.Random(seed)
    ours, theirs = TwoStackQueue(), deque()
    for i in range(500):
        if theirs and rng.random() < 0.45:
            assert ours.get() == theirs.popleft()
        else:
            ours.put(i)
            theirs.append(i)


def test_an_explicit_stack_goes_where_recursion_cannot():
    assert total_recursive(nested(100)) == total_with_a_stack(nested(100)) == sum(range(101))
    deep = nested(50_000)
    with pytest.raises(RecursionError):
        total_recursive(deep)
    assert total_with_a_stack(deep) == 50_000 * 50_001 // 2
