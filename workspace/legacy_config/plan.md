# Refactoring plan: `parse` (key=value config reader)

## 1. Code smells

| Smell | Why it matters |
|---|---|
| Mutable default argument `defaults={}` | The dict is shared across calls, so values from one parse leak into the next. |
| `cfg = defaults` aliasing | Mutates the caller's dict and returns the same object, a hidden side effect. |
| Bare `except:` (twice) | Swallows every exception, including `KeyboardInterrupt`, and hides intent. |
| Exception-driven control flow for "no `=`" | An `IndexError` is used as a validity check. An explicit length check is clearer. |
| `line.split("=")` called twice | It is wasteful and obscures that only the first two segments are used (see quirks in §3). |
| One function does line splitting, filtering, key/value extraction and type coercion | It is hard to test or reason about each concern separately. |
| Unclear names (`k`, `v`, `cfg`) and `v` reassigned across types | Readability suffers, and `v` is str, bool or int at different points. |
| No docstring, type hints or documented coercion rules | The quirks (truncation at second `=`, no inline comments) are undiscoverable. |

## 2. Target design (`refactored.py`)

```python
from typing import Any

def parse(text: str, defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    """Public API, same name and positional signature as the original.
    Start from a shallow copy of `defaults` (or {}), iterate over
    text.split("\n"), apply _parse_line to each, store results by key
    (later wins), and return the new dict."""

def _parse_line(raw_line: str) -> tuple[str, Any] | None:
    """Strip the line. Return None for blank lines, lines starting with
    '#', and lines with no '='. Otherwise split on '=', take
    key = parts[0].strip() and raw_value = parts[1].strip()
    (parts[2:] ignored, as in the original). Return (key, _coerce(raw_value))."""

def _coerce(raw_value: str) -> bool | int | str:
    """'true'/'false' (case-insensitive) -> bool.
    Else try int(raw_value) -> int. On ValueError return raw_value unchanged
    (original case preserved)."""
```

Rules:
- Catch only `ValueError`, and only around `int(...)`.
- Do not use `str.splitlines()`. Keep `split("\n")` to preserve behavior.
- Do not use `split("=", 1)`. It would change the truncation behavior.

## 3. Behavior to preserve

**Line handling**
- Lines are split on `"\n"` only. `"\r\n"` works because `strip()` removes the `\r`. A lone `\r` is not a line separator.
- Each line is stripped. A line that is empty after stripping is skipped.
- A line whose first non-space character is `#` is skipped.
- A line with no `=` is silently skipped, with no error.

**Key and value extraction**
- `key = line.split("=")[0].strip()` and `value = line.split("=")[1].strip()`.
- **Multiple `=`:** only the segment between the first and second `=` is the value.
  - `"a=b=c"` → `{"a": "b"}`
  - `"a==5"` → `{"a": ""}`
- **Empty key:** `"=5"` → `{"": 5}`.
- **Empty value:** `"a="` → `{"a": ""}`, since `int("")` fails and the empty string is kept.
- **No inline comments:** `"a=1 # x"` → `{"a": "1 # x"}`.
- Keys are case-sensitive and are not coerced.

**Type coercion** (applied in this order)
1. `value.lower() == "true"` → `True`, and `"false"` → `False`, in any case (`TRUE`, `False`).
2. Otherwise `int(value)` is attempted. It accepts `"-3"`, `"+5"`, `"007"` (→ 7), and `"1_000"` (→ 1000).
3. Otherwise the stripped string is kept with its original case. Examples: `"1.5"`, `"0x10"`, `"Hello"`.
4. `"1"` and `"0"` become ints, not bools.

**Merging and output**
- Duplicate keys: the last one wins. An overridden key keeps its original insertion position.
- Keys from `defaults` that are absent from the text are kept as-is. Default values are not coerced.
- The result is a plain `dict` with insertion order.
- `parse("")` returns the defaults content (or `{}`).
- A non-string `text` (e.g. `None`) raises `AttributeError`. This is acceptable to preserve, but it is not required to be tested.

## 4. Improvements (intentional changes)

1. **Fix the shared mutable default.** Use `defaults=None` and create a fresh dict per call.
   - Justification: this is a real bug, because state persists between calls when `defaults` is omitted.
2. **Do not mutate the caller's `defaults`.** Work on a shallow copy, so the returned dict is a new object (`result is not defaults`).
   - Justification: this removes the aliasing side effect.
   - Risk: any caller relying on in-place mutation or identity will break. The implementer should grep for call sites if available.
3. **Narrow the bare `except`.** This changes behavior only for `KeyboardInterrupt` and `SystemExit`, which are now no longer swallowed. In practice this is unreachable here.

Deliberately not changed: second-`=` truncation, the lack of inline comments, and `int()` leniency (underscores, `+`). These are quirks, but changing them is out of scope.

## 5. Test plan (pytest)

1. `test_basic_types`: `"a=1\nb=true\nc=hello"` → `{"a": 1, "b": True, "c": "hello"}`.
2. `test_bool_case_insensitive`: `"a=TRUE\nb=False"` → `True` and `False`, with identity checked via `is`.
3. `test_one_and_zero_are_ints`: `"a=1\nb=0"` → values are ints, and `type(v) is int`.
4. `test_negative_plus_and_leading_zero_ints`: `"a=-3\nb=+5\nc=007"` → `-3`, `5`, `7`.
5. `test_non_int_numbers_stay_strings`: `"a=1.5\nb=0x10"` → `"1.5"` and `"0x10"`.
6. `test_whitespace_stripped`: `"  key  =  val  "` → `{"key": "val"}`.
7. `test_comments_and_blank_lines_skipped`: `"# c\n\n   \n  # indented\na=1"` → `{"a": 1}`.
8. `test_line_without_equals_ignored`: `"junk\na=1"` → `{"a": 1}`, with no exception.
9. `test_multiple_equals_truncates`: `"a=b=c"` → `{"a": "b"}` and `"a==5"` → `{"a": ""}`.
10. `test_empty_key_and_empty_value`: `"=5"` → `{"": 5}` and `"a="` → `{"a": ""}`.
11. `test_inline_comment_not_stripped`: `"a=1 # x"` → `{"a": "1 # x"}`.
12. `test_crlf_line_endings`: `"a=1\r\nb=true\r\n"` → `{"a": 1, "b": True}`.
13. `test_duplicate_keys_last_wins_and_defaults_merge`: `parse("a=2\na=3", {"a": 1, "z": "d"})` → `{"a": 3, "z": "d"}`. Also check that the default value is not coerced, e.g. a default `"5"` stays a string if the key is absent from the text.
14. `test_no_shared_state_between_calls`: `parse("a=1")` then `parse("b=2")` → the second result is `{"b": 2}` (Improvement 1).
15. `test_defaults_not_mutated`: after `d = {"x": 1}; r = parse("y=2", d)`, `d == {"x": 1}`, `r == {"x": 1, "y": 2}`, and `r is not d` (Improvement 2).