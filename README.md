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

- `binary_search.py`, `sorting.py`, `hash_table.py`, `recursion.py`, `graphs.py` — the
  implementations, with the traces and diagrams they draw
- `big_o.py` — the timing harness for the complexity article
- `tests/` — pytest suites: each algorithm against a plain scan, `sorted()`, a real
  `dict` or every possible path, plus one test per classic bug that shows how it fails
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

## Licence

MIT, see `LICENSE`. The Lora font files in `fonts/` are under the SIL Open Font License.
