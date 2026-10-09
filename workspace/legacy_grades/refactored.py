from __future__ import annotations

from typing import Any, Iterable, Sequence

GRADE_THRESHOLDS: tuple[tuple[int, str], ...] = (
    (90, "A"),
    (80, "B"),
    (70, "C"),
    (60, "D"),
)
FAILING_GRADE = "F"
HONOR_ROLL_THRESHOLD = 90


def average(scores: Sequence[float]) -> float | int:
    """Return the mean of scores, or the int 0 when scores is empty."""
    if len(scores) == 0:
        return 0
    # Explicit left-to-right accumulation starting from int 0, deliberately
    # not builtin sum(): Python 3.12+ sum() uses compensated float summation,
    # which can change results in the last bits.
    total = 0
    for x in scores:
        total += x
    return total / len(scores)


def letter_grade(avg: float) -> str:
    """Return the letter grade for an unrounded average."""
    for threshold, grade in GRADE_THRESHOLDS:
        if avg >= threshold:
            return grade
    return FAILING_GRADE


def format_report_line(name: str, avg: float, grade: str) -> str:
    """Format one report line; plain concatenation keeps TypeError for non-str names."""
    return name + ": " + str(round(avg, 1)) + " (" + grade + ")"


def calc(students: Iterable[Sequence]) -> list[str]:
    """Return one report line per student record (name, scores, ...)."""
    result = []
    for student in students:
        name, scores = student[0], student[1]
        avg = average(scores)
        grade = letter_grade(avg)
        result.append(format_report_line(name, avg, grade))
    return result


def honor_roll(students: Iterable[Sequence]) -> list:
    """Return names of students whose unrounded average is >= the threshold."""
    names: list[Any] = []
    for student in students:
        scores = student[1]
        if len(scores) > 0 and average(scores) >= HONOR_ROLL_THRESHOLD:
            names.append(student[0])
    return names
