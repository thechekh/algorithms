# algorithms

The algorithms behind the articles on [chekh.dev](https://chekh.dev): implemented in
plain Python so you can read them, tested so you can trust them, traced step by step so
you can see them, and timed so you can feel the difference.

| Script | Article | What it does |
|---|---|---|
| `big_o.py` | [Big-O, measured on your laptop](https://chekh.dev/writing/big-o-measured-on-your-laptop/) | Times five operations, one per complexity class, as the input doubles ten times (about 2 min) |
| `binary_search.py` | [Binary search, and the off-by-one everyone writes](https://chekh.dev/writing/binary-search-and-the-off-by-one-everyone-writes/) | Two correct searches, three classic bugs, and a step-by-step trace |
| `sorting.py` | [Sorting, from bubble sort to Timsort](https://chekh.dev/writing/sorting-from-bubble-sort-to-timsort/) | Four sorts traced on eight numbers, then timed against `sorted()` (about 2 min) |
| `hash_table.py` | [How a hash table works, and why dict lookups are fast](https://chekh.dev/writing/how-a-hash-table-works-and-why-dict-lookups-are-fast/) | A sixty-line hash map timed against a list scan and `dict`, then with resizing off and with bad hash functions (about 1 min) |
| `recursion.py` | [Recursion, drawn](https://chekh.dev/writing/recursion-drawn/) | The call stack for factorial, the call tree for Fibonacci, naive against memoised, and the recursion limit |
| `graphs.py` | [Graphs: BFS and DFS, traced step by step](https://chekh.dev/writing/graphs-bfs-and-dfs-traced-step-by-step/) | BFS and DFS traced on a maze, then compared on 300 random mazes |
| `heaps.py` | [Heaps and priority queues: the array trick behind heapq](https://chekh.dev/writing/heaps-and-priority-queues-the-array-trick-behind-heapq/) | A binary heap traced as it pushes and pops, its comparisons counted two ways, and four ways to find the ten largest of a million numbers (about 1 min) |
| `shortest_paths.py` | [Dijkstra and A*, traced on a weighted grid](https://chekh.dev/writing/dijkstra-and-a-star-traced-on-a-weighted-grid/) | BFS, Dijkstra, A* and greedy search traced on a map with forest, run on 200 random maps, and Dijkstra timed with and without a heap (about 1 min) |
| `dynamic_programming.py` | [Dynamic programming: from recursion to a table](https://chekh.dev/writing/dynamic-programming-from-recursion-to-a-table/) | Coin change and edit distance, each as a plain recursion, with a cache, and as a table (about 5 min, most of it the plain recursions) |
| `arrays_and_lists.py` | [Arrays and linked lists: what "fast" depends on](https://chekh.dev/writing/arrays-and-linked-lists-what-fast-depends-on/) | A linked list timed against `list` and `deque` on four jobs, the memory each uses per item, how a list grows, and one sum in two memory orders (about 2 min) |
| `stacks_and_queues.py` | [Stacks and queues, and the call stack every program runs on](https://chekh.dev/writing/stacks-and-queues-and-the-call-stack/) | A bracket checker and a postfix calculator traced, four queues timed, and a structure 100,000 levels deep walked by recursion and by a loop with a stack (about 1 min) |
| `trees.py` | [Binary search trees, balance, and why databases use B-trees](https://chekh.dev/writing/binary-search-trees-balance-and-why-databases-use-b-trees/) | A plain binary search tree, an AVL tree and a B-tree measured up to a million keys, then SQLite with and without an index, its depth read from the database file (about 2 min) |

## Run it

Needs Python 3.12 and [uv](https://docs.astral.sh/uv/). No accounts, no keys.

```sh
git clone https://github.com/thechekh/algorithms
cd algorithms
uv sync                       # creates .venv with the pinned versions
uv run pytest                 # the tests: every algorithm against the truth
uv run python big_o.py        # or any script in the table
```

The timing scripts print their numbers as they go, write them to `results/<slug>.json`,
and draw their charts to `charts/<slug>/` as SVG; `--charts-only` redraws from the saved
numbers. Timings depend on the machine — the articles quote a desktop with an AMD Ryzen
5 3600 — but the *shapes* do not: a quadratic algorithm doubles its input and takes four
times as long on any computer.

## What is in here

- `binary_search.py`, `sorting.py`, `hash_table.py`, `recursion.py`, `graphs.py`,
  `heaps.py`, `shortest_paths.py`, `dynamic_programming.py`, `arrays_and_lists.py`,
  `stacks_and_queues.py`, `trees.py` — the implementations, with the traces and
  diagrams they draw
- `big_o.py` — the timing harness for the complexity article
- `tests/` — pytest suites: each algorithm against a plain scan, `sorted()`, `heapq`, a
  real `dict`, a Python list or set, Python's own arithmetic, every possible path,
  Bellman-Ford or brute force, plus one test per classic bug that shows how it fails,
  and the SQLite depth reader against real database files
- `_common.py` — shared setup: fonts, chart style, a careful timer, where charts go
- `paper.mplstyle`, `fonts/` — the site's chart style and typeface (Lora, SIL Open Font
  License)
- `results/`, `charts/` — the numbers and charts from the last run

## Change something

- `sorting.py` — add an algorithm to `ALGORITHMS` and it joins the timings and the
  scenario table; break one and `uv run pytest` says which input caught it
- `binary_search.py` — write your own buggy version and add the case that catches it to
  `tests/test_binary_search.py`
- `big_o.py` — add an operation to `OPERATIONS` with a setup function, and its line
  appears on the chart with its measured slope
- `hash_table.py` — pass your own `hash_function=` to `HashMap` and see what it does to
  the chain lengths; change the 0.75 in `put` and rerun the load-factor chart
- `recursion.py` — add a function to `compute()` and its call count joins the table
- `graphs.py` — edit `MAZE` (keep one `S` and one `G`) and both traces redraw; change
  the neighbour order in `neighbours()` and watch DFS take a different route
- `heaps.py` — add a method to `TOP_K` and it joins the timing chart
- `shortest_paths.py` — edit `MAP` or the costs in `Grid.COSTS`; multiply the guess in
  `a_star` by 2 and watch it expand fewer cells and sometimes miss the cheapest path
- `dynamic_programming.py` — change `COINS` and see for which amounts the greedy answer
  goes wrong; the tests check every version against brute force
- `arrays_and_lists.py` — change `n` in `memory_order` and find how small the data must
  be before the shuffled order stops costing anything
- `stacks_and_queues.py` — add an operator such as `%` to `PRECEDENCE`, `APPLY` and
  `TOKEN`; find the deepest nesting `total_recursive` survives, and work out why it is
  not 1,000
- `trees.py` — change the `t` passed to `BTree` and watch the height and the nodes
  visited change; raise `rows` in `sqlite_demo` and find where the index grows a fourth
  level

## Licence

MIT, see `LICENSE`. The Lora font files in `fonts/` are under the SIL Open Font License.
