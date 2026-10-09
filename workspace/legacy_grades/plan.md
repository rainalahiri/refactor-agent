# Refactoring Plan: grade calculator

## 1. Code smells

| Smell | Why it matters |
|---|---|
| Cryptic names (`calc`, `s`, `g`, `total`) | The reader can't tell what the function computes or what `s[0]` and `s[1]` mean. |
| Magic indexes `s[0]` and `s[1]` | The record format (name, scores) is implicit and undocumented. |
| Duplicated averaging logic in `calc` and `honor_roll` | The two copies can drift apart, and the 90 threshold is repeated. |
| `for i in range(len(...))` with manual summing | It is unidiomatic, noisy, and recomputes `len` repeatedly. |
| Nested `else: if` ladder for grades | The ladder is deeply indented and hard to extend. The thresholds are buried in control flow. |
| Magic numbers (90, 80, 70, 60) and a magic string `"F"` | They are unnamed and scattered. |
| `calc` mixes computation, grading, and formatting | It can't be tested or reused in pieces. |
| String building with `+` and `str()` | It is hard to read and error-prone. |
| No docstrings or type hints | Input and output contracts are undefined. |
| Empty-scores case returns int `0` via an inline `else` | The quirk is accidental and undocumented (see section 3). |

## 2. Target design (`refactored.py`)

```python
from typing import Sequence, Iterable, Any

GRADE_THRESHOLDS: tuple[tuple[int, str], ...] = ((90, "A"), (80, "B"), (70, "C"), (60, "D"))
FAILING_GRADE = "F"
HONOR_ROLL_THRESHOLD = 90
```

- `average(scores: Sequence[float]) -> float | int`
  - Returns `0` (an **int**) for empty scores.
  - Otherwise returns `total / len(scores)`.
  - `total` is accumulated with an explicit left-to-right loop (`total = 0; for x in scores: total += x`), **not** builtin `sum()`. In Python 3.12+, `sum()` uses compensated float summation, which can change results in the last bits.
  - Add a comment explaining this.

- `letter_grade(avg: float) -> str`
  - Iterates `GRADE_THRESHOLDS` in order and returns the first grade where `avg >= threshold`.
  - Returns `FAILING_GRADE` otherwise.
  - Takes the **unrounded** average.

- `format_report_line(name: str, avg: float, grade: str) -> str`
  - Returns `name + ": " + str(round(avg, 1)) + " (" + grade + ")"`.
  - An f-string is fine only if `name` is already a `str`. Plain concatenation preserves the `TypeError` for non-str names.

- `calc(students: Iterable[Sequence]) -> list[str]`
  - Public name kept.
  - For each record, unpack `name, scores = student[0], student[1]`. Do **not** use `name, scores = student`, because records with extra elements must still work.
  - Calls `average`, `letter_grade`, and `format_report_line`, and returns a list in input order.

- `honor_roll(students: Iterable[Sequence]) -> list`
  - Public name kept.
  - Includes `student[0]` (unchanged, no `str()`) when `len(scores) > 0 and average(scores) >= HONOR_ROLL_THRESHOLD`.
  - Returns a list in input order.

## 3. Behavior to preserve

- **Public API:** `calc` and `honor_roll` keep their names and take one positional argument. The input is an iterable of records. Each record is indexable, with `[0]` the name and `[1]` the scores. The scores are a sized, indexable sequence of numbers. Extra record elements are ignored.
- **`calc` output format:** one string per student, `"<name>: <rounded avg> (<grade>)"`, in input order.
- **Empty students list:** both functions return `[]`.
- **Empty scores in `calc`:** avg is the int `0`, so the output is `"Name: 0 (F)"`. It is **not** `"0.0"`, because `round(0, 1)` returns int `0`.
- **Non-empty scores:** avg is a float from true division, so integer inputs still display as `"85.0"`.
- **Rounding:** the builtin `round(avg, 1)` is used, so banker's rounding and float representation quirks are unchanged.
- **Grade from unrounded average:** `[89.96]` displays `"90.0 (B)"`.
- **Boundaries are inclusive:** 90→A, 80→B, 70→C, 60→D. Below 60, including negative averages, is F. There is no upper clamp, so 150 → A.
- **`honor_roll` threshold:** it uses the unrounded avg `>= 90`, and empty-score students are excluded. Names are returned as-is (any type) and in input order.
- **Errors propagate unchanged and no partial result is returned:**
  - Non-str name in `calc` → `TypeError`.
  - Non-numeric score → `TypeError`.
  - Record missing `[1]` → `IndexError`.
  - Scores without `len` or indexing, e.g. a generator → `TypeError`.
  - `honor_roll` does not require `name` to be a str.
- **No mutation of inputs** and no I/O. Each call returns a new list.
- **Float summation:** the left-to-right order starting from int `0` is preserved (see `average`).

## 4. Improvements

None to behavior. Additions are non-behavioral:
- Docstrings and type hints.
- Named constants for thresholds.

Quirks such as the `"0"` vs `"0.0"` output and the strict str name requirement are deliberately **kept**. Fixing them is out of scope and would be a separate, announced change.

## 5. Test plan (pytest, 15 tests)

Tests import from `refactored`. Test 15 embeds a verbatim copy of the legacy code as an oracle.

1. `test_calc_basic`: `[("Ann", [90, 100])]` → `["Ann: 95.0 (A)"]`.
2. `test_calc_preserves_order_and_multiple_students`: three students with different grades come out in input order.
3. `test_grade_boundaries` (parametrized): averages 90, 89.9, 80, 79.9, 70, 69.9, 60, 59.9 give A, B, B, C, C, D, D, F.
4. `test_calc_empty_scores_outputs_int_zero`: `[("Bob", [])]` → `["Bob: 0 (F)"]`.
5. `test_calc_empty_students`: `calc([]) == []`.
6. `test_grade_uses_unrounded_average`: `[("X", [89.96])]` → `["X: 90.0 (B)"]`.
7. `test_calc_integer_scores_display_as_float`: `[("Y", [80, 80])]` → `"Y: 80.0 (B)"`.
8. `test_calc_negative_and_over_100`: `[-10]` → F with `"-10.0"`, and `[150]` → A.
9. `test_calc_extra_record_elements_ignored`: `("Z", [70], "extra")` works.
10. `test_calc_non_str_name_raises_typeerror`: `(123, [90])` raises `TypeError`.
11. `test_calc_bad_score_raises`: a record with `["a"]` scores raises `TypeError`, and no partial result is returned.
12. `test_honor_roll_basic_and_order`: only students with avg ≥ 90 are returned, in input order.
13. `test_honor_roll_boundary_and_empty_scores`: avg exactly 90 is included, 89.99 is excluded, empty scores are excluded, and `honor_roll([]) == []`.
14. `test_honor_roll_returns_names_unchanged`: a non-str name (e.g. `42`) is returned as-is, with no error.
15. `test_matches_legacy_oracle`: using a fixed seed, generate about 200 random students with 0–6 int or float scores. Assert `calc` and `honor_roll` equal the legacy outputs exactly. This also guards against float summation drift and rounding differences.