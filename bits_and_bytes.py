"""Bits, bytes and numbers: what a computer actually stores.

Article: https://chekh.dev/writing/bits-bytes-and-numbers-what-a-computer-actually-stores/
Run:     uv run python bits_and_bytes.py                (a few seconds)
         uv run python bits_and_bytes.py --charts-only  (redraw from results/)
         uv run pytest tests/test_bits_and_bytes.py

Integers in two's complement and what happens when they overflow, 64-bit floats taken
apart bit by bit, the gaps between neighbouring floats, the error of adding 0.1 many
times in six ways, and text as UTF-8 bytes, encoded by hand and checked against Python.
"""

import datetime
import json
import math
import struct
import sys
import unicodedata
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from _common import ACCENT, DANGER, INK, INK_2, MUTED, machine, plain_numbers, save

SLUG = "bits-bytes-and-numbers-what-a-computer-actually-stores"


# --- Integers -------------------------------------------------------------------------------


def bits(value: int, width: int) -> str:
    """The pattern that stores `value` in `width` bits, in two's complement if negative."""
    return format(value % 2**width, f"0{width}b")


def signed(pattern: str) -> int:
    """Two's complement: the top bit is worth -2**(n-1), the rest as usual."""
    top = -(2 ** (len(pattern) - 1)) if pattern[0] == "1" else 0
    return top + int(pattern[1:], 2)


def negate(pattern: str) -> str:
    """Two's-complement negation: flip every bit, then add one."""
    flipped = "".join("1" if b == "0" else "0" for b in pattern)
    return bits(int(flipped, 2) + 1, len(pattern))


def integers() -> dict:
    out = {"ranges": {f"int{w}": [-(2 ** (w - 1)), 2 ** (w - 1) - 1] for w in (8, 16, 32, 64)}}
    out["int8 127 + 1"] = int((np.array([127], dtype=np.int8) + 1)[0])  # arrays wrap silently
    out["int32 max + 1"] = int((np.array([2**31 - 1], dtype=np.int32) + 1)[0])
    epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    out["last second in signed 32 bits"] = str(epoch + datetime.timedelta(seconds=2**31 - 1))
    out["python int sizes"] = {label: sys.getsizeof(v) for label, v in
                               [("0", 0), ("1", 1), ("2**30", 2**30), ("2**60", 2**60), ("2**100", 2**100),
                                ("2**1000", 2**1000)]}
    out["2**1000 digits"] = len(str(2**1000))
    return out


# --- Floats ---------------------------------------------------------------------------------


def float_parts(x: float) -> dict:
    """Sign, exponent and fraction of a 64-bit float, and the exact value stored."""
    raw = int.from_bytes(struct.pack(">d", x), "big")
    sign, exponent, fraction = raw >> 63, (raw >> 52) & 0x7FF, raw & (2**52 - 1)
    return {"bits": format(raw, "064b"), "sign": sign, "exponent": exponent - 1023,
            "fraction": fraction, "exact": str(Decimal(x))}


def float32_parts(x: float) -> dict:
    raw = int.from_bytes(struct.pack(">f", x), "big")
    return {"bits": format(raw, "032b"), "sign": raw >> 31, "exponent": ((raw >> 23) & 0xFF) - 127,
            "fraction": raw & (2**23 - 1), "exact": str(Decimal(float(np.float32(x))))}


def from_parts(sign: int, exponent: int, fraction: int) -> float:
    """Rebuild a normal 64-bit float: (-1)**sign * (1 + fraction / 2**52) * 2**exponent."""
    return (-1) ** sign * (1 + fraction / 2**52) * 2.0**exponent


def gaps() -> dict:
    """The distance from x to the next float up, for float64 and float32."""
    xs = np.logspace(-6, 20, 600)
    return {"x": xs.tolist(), "float64": [math.ulp(float(x)) for x in xs],
            "float32": [float(np.spacing(np.float32(x))) for x in xs],
            "gap after 1.0": math.ulp(1.0), "gap at 2**53": math.ulp(2.0**53), "gap at 1e16": math.ulp(1e16),
            "float32 gap after 1.0": float(np.spacing(np.float32(1))),
            "float32 gap at 2**24": float(np.spacing(np.float32(2**24))),
            "float32 gap at 1e6": float(np.spacing(np.float32(1e6))),
            "float32 0.1 added to 1e6": float(np.float32(1e6) + np.float32(0.1)) - 1e6,
            "2**53 + 1 == 2**53 as floats": 2.0**53 + 1 == 2.0**53,
            "float32 2**24 + 1 == 2**24": bool(np.float32(2**24) + np.float32(1) == np.float32(2**24)),
            "float_info": {"mant_dig": sys.float_info.mant_dig, "dig": sys.float_info.dig,
                           "epsilon": sys.float_info.epsilon, "max": sys.float_info.max,
                           "min (smallest normal)": sys.float_info.min}}


def add_tenths(n: int) -> dict:
    """Add 0.1 to itself n times in six ways; each result and its relative error."""
    tenth64, tenth32 = 0.1, np.float32(0.1)
    exact64 = Fraction(tenth64) * n  # the true sum of the values actually stored
    exact32 = Fraction(float(tenth32)) * n
    a64, a32 = np.full(n, tenth64), np.full(n, tenth32, dtype=np.float32)
    many = [tenth64] * n
    results = {
        "a loop, float64": float(np.cumsum(a64)[-1]),  # one addition after another
        "sum(), Python 3.12": sum(many),  # compensated summation since 3.12
        "numpy.sum, float64": float(a64.sum()),  # pairwise summation
        "math.fsum": math.fsum(many),  # the exactly rounded sum
        "a loop, float32": float(np.cumsum(a32)[-1]),
        "numpy.sum, float32": float(a32.sum()),
    }
    errors = {}
    for name, value in results.items():
        exact = exact32 if "float32" in name else exact64
        errors[name] = float(abs(Fraction(value) - exact) / exact)
    return {"results": results, "errors": errors}


# --- Text -----------------------------------------------------------------------------------


def utf8(code_point: int) -> bytes:
    """Encode one code point by hand, following the table in RFC 3629."""
    if code_point < 0x80:
        return bytes([code_point])  # 0xxxxxxx
    if code_point < 0x800:
        return bytes([0b11000000 | (code_point >> 6),  # 110xxxxx
                      0b10000000 | (code_point & 0b111111)])  # 10xxxxxx
    if code_point < 0x10000:
        return bytes([0b11100000 | (code_point >> 12),
                      0b10000000 | ((code_point >> 6) & 0b111111),
                      0b10000000 | (code_point & 0b111111)])
    return bytes([0b11110000 | (code_point >> 18),
                  0b10000000 | ((code_point >> 12) & 0b111111),
                  0b10000000 | ((code_point >> 6) & 0b111111),
                  0b10000000 | (code_point & 0b111111)])


CHARACTERS = ["A", "\u00e9", "\u0416", "\u20ac", "\u4e2d", "\U0001f44d"]  # A, é, Ж, €, 中, thumbs up


def text() -> dict:
    chars = []
    for ch in CHARACTERS:
        encoded = ch.encode("utf-8")
        chars.append({"char": ch, "code point": f"U+{ord(ch):04X}", "name": unicodedata.name(ch),
                      "utf8 hex": encoded.hex(" "), "utf8 bits": " ".join(f"{b:08b}" for b in encoded),
                      "utf8 bytes": len(encoded), "utf16 units": len(ch.encode("utf-16-le")) // 2,
                      "by hand matches": utf8(ord(ch)) == encoded})
    strings = {}
    for label, last in [("ASCII only", "a"), ("one e-acute", "\u00e9"), ("one euro sign", "\u20ac"),
                        ("one thumbs up", "\U0001f44d")]:
        s = "a" * 999 + last
        strings[label] = {"len": len(s), "in memory": sys.getsizeof(s), "as UTF-8": len(s.encode("utf-8"))}
    family = "\U0001f468\u200d\U0001f469\u200d\U0001f467"  # man, zero-width joiner, woman, joiner, girl
    composed, decomposed = "\u00e9", "e\u0301"
    return {"characters": chars, "1,000-character strings": strings,
            "family emoji": {"len": len(family), "utf8 bytes": len(family.encode("utf-8")),
                             "code points": [f"U+{ord(c):04X}" for c in family]},
            "composed == decomposed": composed == decomposed, "len decomposed": len(decomposed),
            "equal after NFC": unicodedata.normalize("NFC", decomposed) == composed}


def surprises() -> dict:
    """Each expression, evaluated, as the article's table shows it."""
    return {
        "0.1 + 0.2": repr(0.1 + 0.2),
        "0.1 + 0.2 == 0.3": repr(0.1 + 0.2 == 0.3),
        "math.isclose(0.1 + 0.2, 0.3)": repr(math.isclose(0.1 + 0.2, 0.3)),
        "1e16 + 1 == 1e16": repr(1e16 + 1 == 1e16),
        "round(2.675, 2)": repr(round(2.675, 2)),
        "float('nan') == float('nan')": repr(float("nan") == float("nan")),
        "-7 // 2": repr(-7 // 2),
        "int(-7 / 2)": repr(int(-7 / 2)),
        "np.array([127], dtype=np.int8) + 1": repr(int((np.array([127], dtype=np.int8) + 1)[0])),
        "len('\U0001f44d'), len('\U0001f44d'.encode())": repr((len("\U0001f44d"), len("\U0001f44d".encode()))),
        "'\u00e9' == 'e\\u0301'": repr("\u00e9" == "e\u0301"),
    }


def compute() -> dict:
    results: dict = {"machine": machine(), "numpy": np.__version__, "byteorder": sys.byteorder}
    results["examples"] = {"5": bits(5, 8), "-5": bits(-5, 8), "negate 5": negate(bits(5, 8)),
                           "signed 11111011": signed("11111011")}
    results["integers"] = integers()
    print("int8 127 + 1 ->", results["integers"]["int8 127 + 1"], "| int32 max + 1 ->", results["integers"]["int32 max + 1"],
          "| 2**31 - 1 seconds after 1970:", results["integers"]["last second in signed 32 bits"])
    print("Python int sizes:", results["integers"]["python int sizes"])
    results["floats"] = {"0.1": float_parts(0.1), "0.2": float_parts(0.2), "0.1 + 0.2": float_parts(0.1 + 0.2),
                         "0.3": float_parts(0.3), "float32 0.1": float32_parts(0.1)}
    for k, v in results["floats"].items():
        print(f"{k:>11}: exponent {v['exponent']:3d}, exact value {v['exact']}")
    results["gaps"] = gaps()
    print("gap after 1.0:", results["gaps"]["gap after 1.0"], "| at 2**53:", results["gaps"]["gap at 2**53"],
          "| float32 after 1.0:", results["gaps"]["float32 gap after 1.0"])
    sizes = [10, 100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000]
    results["tenths"] = {"sizes": sizes, "runs": [add_tenths(n) for n in sizes]}
    for n, run in zip(sizes, results["tenths"]["runs"]):
        print(f"n = {n:>10,}: " + "  ".join(f"{k}: {v!r}" for k, v in run["results"].items()))
    results["text"] = text()
    for c in results["text"]["characters"]:
        print(f"{c['code point']:>8} {c['utf8 bits']:<36} {c['utf8 bytes']} bytes in UTF-8, "
              f"{c['utf16 units']} UTF-16 units, by hand ok: {c['by hand matches']}")
    print("1,000-character strings:", results["text"]["1,000-character strings"])
    results["surprises"] = surprises()
    for k, v in results["surprises"].items():
        print(f"  {k.encode('ascii', 'backslashreplace').decode():44s} -> {v.encode('ascii', 'backslashreplace').decode()}")
    return results


# --- Charts ---------------------------------------------------------------------------------


def _cells(ax, x, y, pattern, fills, fontsize=8.5, w=1.0, h=1.0):
    for i, (bit, fill) in enumerate(zip(pattern, fills)):
        ax.add_patch(plt.Rectangle((x + i * w, y), w, h, facecolor=fill, edgecolor=INK_2, linewidth=0.8))
        ax.text(x + i * w + w / 2, y + h / 2, bit, ha="center", va="center", fontsize=fontsize, color=INK)


def _brace(ax, x0, x1, y, label, color=INK_2):
    ax.plot([x0 + 0.1, x0 + 0.1, x1 - 0.1, x1 - 0.1], [y + 0.25, y, y, y + 0.25], color=color, linewidth=0.9)
    ax.text((x0 + x1) / 2, y - 0.35, label, ha="center", va="top", fontsize=7.8, color=color)


def draw_bits(results: dict) -> None:
    """The same idea four times: bits, and the rule that says what they mean."""
    fig, ax = plt.subplots(figsize=(8.6, 5.6))
    ax.set_xlim(-0.2, 33.4)
    ax.set_ylim(-13.0, 2.6)
    ax.axis("off")
    light, pale, white = "#dfe5df", "#faf9f6", "white"

    weights = ["-128", "64", "32", "16", "8", "4", "2", "1"]
    for row, (value, title, y) in enumerate([(5, "5 as an 8-bit integer", 0.0), (-5, "-5 as an 8-bit integer", -3.0)]):
        pattern = bits(value, 8)
        ax.text(0, y + 1.75 if row == 0 else y + 1.05, title, fontsize=9.2, color=INK, va="bottom")
        _cells(ax, 0, y - 0.2, pattern, [light] + [pale] * 7)
        if row == 0:
            for i, wt in enumerate(weights):
                ax.text(i + 0.5, y + 0.95, wt, ha="center", va="bottom", fontsize=7, color=ACCENT if i == 0 else INK_2)
        used = [wt for wt, b in zip(weights, pattern) if b == "1"]
        ax.text(8.6, y + 0.3, "= " + " + ".join(used).replace("+ -", "- ") + f" = {value}", fontsize=8.6, color=INK, va="center")
    ax.text(21.5, 2.3, "the top bit is worth -128,\nso any pattern that starts\nwith 1 is negative", fontsize=8,
            color=ACCENT, va="top")

    f = results["floats"]["float32 0.1"]
    y = -6.4
    ax.text(0, y + 1.05, "0.1 as a 32-bit float", fontsize=9.2, color=INK, va="bottom")
    _cells(ax, 0, y - 0.2, f["bits"], [white] + [light] * 8 + [pale] * 23, fontsize=7.6)
    _brace(ax, 0, 1, y - 0.45, "sign")
    _brace(ax, 1, 9, y - 0.45, f"exponent: {int(f['bits'][1:9], 2)} - 127 = {f['exponent']}")
    _brace(ax, 9, 32, y - 0.45, "fraction, after an implied 1.: 1001 1001 1001 ..., rounded where it stops")
    ax.text(0, y - 1.75, f"stored exactly: {f['exact']}", fontsize=8.2, color=INK_2, va="top")

    enc = results["text"]["characters"][1]
    y = -11.6
    ax.text(0, y + 1.05, f"\u00e9 (code point {enc['code point']}, 233) as UTF-8: two bytes", fontsize=9.2, color=INK, va="bottom")
    pattern = enc["utf8 bits"].replace(" ", "")
    fills = [light] * 3 + [pale] * 5 + [light] * 2 + [pale] * 6
    _cells(ax, 0, y - 0.2, pattern[:8], fills[:8])
    _cells(ax, 8.6, y - 0.2, pattern[8:], fills[8:])
    _brace(ax, 0, 3, y - 0.45, "110: first of two")
    _brace(ax, 8.6, 10.6, y - 0.45, "10: continues")
    ax.text(17.6, y + 0.3, "the other bits, 00011 101001, read together: 233", fontsize=8.6, color=INK, va="center")
    save(fig, SLUG, "bits")


def draw_wheel() -> None:
    """Sixteen 4-bit patterns around a circle, read as two's complement."""
    fig, ax = plt.subplots(figsize=(5.6, 5.4))
    ax.set_xlim(-1.75, 1.75)
    ax.set_ylim(-1.7, 1.7)
    ax.set_aspect("equal")
    ax.axis("off")
    for k in range(16):
        angle = np.pi / 2 - 2 * np.pi * k / 16  # 0000 at the top, counting clockwise
        pattern = bits(k, 4)
        value = signed(pattern)
        x, y = np.cos(angle), np.sin(angle)
        negative = value < 0
        ax.add_patch(plt.Circle((x, y), 0.15, facecolor="#dfe5df" if negative else "#faf9f6", edgecolor=INK_2, linewidth=0.9))
        ax.text(x, y, str(value), ha="center", va="center", fontsize=9, color=INK)
        ax.text(1.36 * x, 1.36 * y, pattern, ha="center", va="center", fontsize=8, color=INK_2)
    ax.annotate("", xy=(np.cos(np.pi / 2 - 2 * np.pi * 8 / 16) * 0.72, np.sin(np.pi / 2 - 2 * np.pi * 8 / 16) * 0.72 + 0.02),
                xytext=(np.cos(np.pi / 2 - 2 * np.pi * 7 / 16) * 0.72, np.sin(np.pi / 2 - 2 * np.pi * 7 / 16) * 0.72),
                arrowprops={"arrowstyle": "-|>", "color": DANGER, "linewidth": 1.2, "connectionstyle": "arc3,rad=-0.3"})
    ax.text(0, -0.42, "7 + 1 = -8:\nthe count wraps", ha="center", va="center", fontsize=8.4, color=DANGER)
    ax.text(0, 0.25, "adding 1 moves\none step clockwise", ha="center", va="center", fontsize=8.4, color=INK_2)
    save(fig, SLUG, "wheel")


def draw_gaps(results: dict) -> None:
    g = results["gaps"]
    fig, ax = plt.subplots(figsize=(6.8, 3.9))
    ax.plot(g["x"], g["float32"], color=INK_2, linewidth=1.4, label="float32")
    ax.plot(g["x"], g["float64"], color=ACCENT, linewidth=1.8, label="float64, Python's float")
    ax.axhline(1, color=MUTED, linewidth=0.9, linestyle="--")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.text(2e-6, 2.2, "a gap of 1", fontsize=7.8, color=INK_2)
    ax.annotate("from 2^53, gaps of 2:\nsome whole numbers\nare skipped", (2.0**53, 2.0), xytext=(14, -34), textcoords="offset points",
                fontsize=7.8, color=ACCENT, va="top", arrowprops={"arrowstyle": "-", "color": ACCENT, "linewidth": 0.8})
    ax.annotate("from 2^24,\ngaps of 2", (2.0**24, 2.0), xytext=(-14, 30), textcoords="offset points", fontsize=7.8,
                color=INK_2, ha="right", va="bottom", arrowprops={"arrowstyle": "-", "color": INK_2, "linewidth": 0.8})
    ax.text(g["x"][-1], g["float64"][-1], "  float64", fontsize=8.5, color=ACCENT, va="center")
    ax.text(g["x"][-1], g["float32"][-1], "  float32", fontsize=8.5, color=INK_2, va="center")
    ax.set_xlim(1e-6, 1e22)
    ax.set_xlabel("the number (log scale)")
    ax.set_ylabel("gap to the next float (log scale)")
    ax.set_title("The gap between neighbouring floats grows with the number", fontsize=10)
    save(fig, SLUG, "gaps")


def draw_tenths(results: dict) -> None:
    sizes = results["tenths"]["sizes"]
    names = list(results["tenths"]["runs"][0]["errors"])
    styles = {"a loop, float64": (INK, "-"), "sum(), Python 3.12": (ACCENT, "-"), "numpy.sum, float64": (INK_2, ":"),
              "math.fsum": (MUTED, "-"), "a loop, float32": (DANGER, "-"), "numpy.sum, float32": (DANGER, ":")}
    floor = 1e-18
    careful = {"sum(), Python 3.12", "numpy.sum, float64", "math.fsum"}  # all within a rounding or two
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    for name in names:
        errs = [max(run["errors"][name], floor) for run in results["tenths"]["runs"]]
        color, style = styles[name]
        ax.plot(sizes, errs, color=color, linestyle=style, linewidth=1.8 if style == "-" else 1.4, marker="o", markersize=3,
                markeredgecolor="white", markeredgewidth=0.6, zorder=3 if color == ACCENT else 2)
        if name not in careful:
            ax.text(sizes[-1] * 1.4, errs[-1], name, fontsize=8, color=color, va="center")
    ax.text(sizes[-1] * 1.4, 1.2e-16, "sum() in Python 3.12,\nnumpy.sum and math.fsum,\nall float64", fontsize=8,
            color=ACCENT, va="center")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks([10, 1_000, 100_000, 10_000_000])
    plain_numbers(ax.xaxis)
    ax.set_xlim(7, 3e9)
    ax.set_ylim(floor / 3, 1)
    ax.set_xlabel("how many times 0.1 is added (log scale)")
    ax.set_ylabel("relative error (log scale)")
    ax.set_title("Adding 0.1 again and again: the error depends on how you add", fontsize=10)
    save(fig, SLUG, "tenths")


if __name__ == "__main__":
    path = Path(__file__).parent / "results" / f"{SLUG}.json"
    if "--charts-only" in sys.argv:
        results = json.loads(path.read_text(encoding="utf-8"))
    else:
        results = compute()
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"  wrote {path.name}")
    draw_bits(results)
    draw_wheel()
    draw_gaps(results)
    draw_tenths(results)
