"""All three trees agree with a set; the AVL tree stays balanced; B-tree nodes stay in bounds."""

import math
import random
import sqlite3

import pytest

from trees import AVL, BST, BTree, height, in_order, index_depth


def check_avl(node) -> int:
    if node is None:
        return 0
    left, right = check_avl(node.left), check_avl(node.right)
    assert abs(left - right) <= 1 and node.height == 1 + max(left, right)
    return node.height


def check_btree(node, t, is_root=True):
    assert len(node.keys) <= 2 * t - 1 and (is_root or len(node.keys) >= t - 1)
    assert node.keys == sorted(node.keys)
    if node.children:
        assert len(node.children) == len(node.keys) + 1
        for child in node.children:
            check_btree(child, t, is_root=False)


@pytest.mark.parametrize("seed", range(15))
def test_all_three_trees_agree_with_a_set(seed):
    rng = random.Random(seed)
    keys = [rng.randrange(500) for _ in range(300)]  # with duplicates
    bst, avl, bt = BST(keys), AVL(keys), BTree(3, keys)
    expected = sorted(set(keys))
    assert in_order(bst.root) == in_order(avl.root) == list(bt) == expected
    for probe in range(0, 520, 7):
        found = probe in set(keys)
        assert bst.search(probe)[0] == avl.search(probe)[0] == bt.search(probe)[0] == found
    check_avl(avl.root)
    check_btree(bt.root, 3)


def test_sorted_input_turns_a_bst_into_a_list_but_not_an_avl_tree():
    assert height(BST(range(500)).root) == 500
    avl = AVL(range(500))
    assert height(avl.root) <= 1.45 * math.log2(502)
    check_avl(avl.root)


def test_a_b_tree_stays_shallow():
    bt = BTree(64, random.Random(0).sample(range(10**6), 100_000))
    assert bt.height() == 3
    check_btree(bt.root, 64)
    assert bt.search(-1) == (False, 3)


@pytest.mark.parametrize("rows, levels", [(10, 1), (10_000, 2), (100_000, 3)])
def test_index_depth_read_from_the_file(tmp_path, rows, levels):
    path = str(tmp_path / "users.db")
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)")
    db.executemany("INSERT INTO users (email) VALUES (?)",
                   ((f"user{i:07d}@example.com",) for i in range(rows)))
    db.execute("CREATE INDEX users_email ON users (email)")
    db.commit()
    root = db.execute("SELECT rootpage FROM sqlite_master WHERE name = 'users_email'").fetchone()[0]
    page_size = db.execute("PRAGMA page_size").fetchone()[0]
    db.close()
    depth, root_keys = index_depth(path, root, page_size)
    assert depth == levels
    assert root_keys == rows if levels == 1 else 1 <= root_keys < rows
