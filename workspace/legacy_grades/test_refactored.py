import random

import pytest

import refactored
from refactored import calc, honor_roll


def test_calc_basic():
    assert calc([("Ann", [90, 100])]) == ["Ann: 95.0 (A)"]


def test_calc_preserves_order_and_multiple_students():
    students = [("A", [50]), ("B", [95]), ("C", [75])]
    assert calc(students) == ["A: 50.0 (F)", "B: 95.0 (A)", "C: 75.0 (C)"]


@pytest.mark.parametrize(
    "avg,grade",
    [
        (90, "A"),
        (89.9, "B"),
        (80, "B"),
        (79.9, "C"),
        (70, "C"),
        (69.9, "D"),
        (60, "D"),
        (59.9, "F"),
    ],
)
def test_grade_boundaries(avg, grade):
    out = calc([("S", [avg])])
    assert out[0].endswith("(" + grade + ")")


def test_calc_empty_scores_outputs_int_zero():
    assert calc([("Bob", [])]) == ["Bob: 0 (F)"]


def test_calc_empty_students():
    assert calc([]) == []


def test_grade_uses_unrounded_average():
    assert calc([("X", [89.96])]) == ["X: 90.0 (B)"]


def test_calc_integer_scores_display_as_float():
    assert calc([("Y", [80, 80])]) == ["Y: 80.0 (B)"]


def test_calc_negative_and_over_100():
    assert calc([("N", [-10])]) == ["N: -10.0 (F)"]
    assert calc([("O", [150])]) == ["O: 150.0 (A)"]


def test_calc_extra_record_elements_ignored():
    assert calc([("Z", [70], "extra")]) == ["Z: 70.0 (C)"]


def test_calc_non_str_name_raises_typeerror():
    with pytest.raises(TypeError):
        calc([(123, [90])])


def test_calc_bad_score_raises():
    with pytest.raises(TypeError):
        calc([("Good", [90]), ("Bad", ["a"])])


def test_honor_roll_basic_and_order():
    students = [("A", [95]), ("B", [50]), ("C", [90, 100]), ("D", [89])]
    assert honor_roll(students) == ["A", "C"]


def test_honor_roll_boundary_and_empty_scores():
    students = [("Exact", [90]), ("Under", [89.99]), ("Empty", [])]
    assert honor_roll(students) == ["Exact"]
    assert honor_roll([]) == []


def test_honor_roll_returns_names_unchanged():
    assert honor_roll([(42, [100])]) == [42]


# ---- legacy oracle ----
def _legacy_calc(students):
    result = []
    for s in students:
        total = 0
        for i in range(len(s[1])):
            total = total + s[1][i]
        if len(s[1]) > 0:
            avg = total / len(s[1])
        else:
            avg = 0
        if avg >= 90:
            g = "A"
        else:
            if avg >= 80:
                g = "B"
            else:
                if avg >= 70:
                    g = "C"
                else:
                    if avg >= 60:
                        g = "D"
                    else:
                        g = "F"
        result.append(s[0] + ": " + str(round(avg, 1)) + " (" + g + ")")
    return result


def _legacy_honor_roll(students):
    names = []
    for s in students:
        total = 0
        for i in range(len(s[1])):
            total = total + s[1][i]
        if len(s[1]) > 0 and total / len(s[1]) >= 90:
            names.append(s[0])
    return names


def test_matches_legacy_oracle():
    rng = random.Random(12345)
    students = []
    for i in range(200):
        n = rng.randint(0, 6)
        scores = []
        for _ in range(n):
            if rng.random() < 0.5:
                scores.append(rng.randint(40, 100))
            else:
                scores.append(rng.uniform(40, 100))
        students.append(("S" + str(i), scores))
    assert calc(students) == _legacy_calc(students)
    assert honor_roll(students) == _legacy_honor_roll(students)
