"""Unit tests for the pure answer-checking logic (no DB, no framework)."""

from __future__ import annotations

import pytest

from ogebot.db.models import AnswerType
from ogebot.services.grading import (
    check_answer,
    normalize_sequence,
    normalize_text,
)


@pytest.mark.parametrize(
    ("user", "reference", "expected"),
    [
        ("60", "60", True),
        (" 60 ", "60", True),
        ("13,7", "13.7", True),  # comma decimal separator
        ("13.70", "13.7", True),  # trailing zero
        ("0,4", "0.4", True),
        ("200", "201", False),
        ("abc", "60", False),  # non-numeric falls back to sequence, still no match
    ],
)
def test_number_answers(user: str, reference: str, expected: bool) -> None:
    assert check_answer(user, [reference], AnswerType.NUMBER) is expected


@pytest.mark.parametrize(
    ("user", "reference", "expected"),
    [
        ("11011", "11011", True),
        ("1 10 11", "11011", True),  # separators ignored, order preserved
        ("2,3,1", "231", True),
        ("321", "231", False),  # order matters
    ],
)
def test_sequence_answers(user: str, reference: str, expected: bool) -> None:
    assert check_answer(user, [reference], AnswerType.SEQUENCE) is expected


@pytest.mark.parametrize(
    ("user", "reference", "expected"),
    [
        ("Москва", "москва", True),
        ("  Москва.", "Москва", True),  # trailing punctuation + spaces
        ("ёлка", "елка", True),  # ё ≈ е
        ("Питер", "Москва", False),
    ],
)
def test_text_answers(user: str, reference: str, expected: bool) -> None:
    assert check_answer(user, [reference], AnswerType.TEXT) is expected


def test_multiple_accepted_answers() -> None:
    assert check_answer("2/5", ["0.4", "2/5"], AnswerType.TEXT) is True
    assert check_answer("0.5", ["0.4", "2/5"], AnswerType.NUMBER) is False


def test_normalizers() -> None:
    assert normalize_text("  Привет,  Мир! ") == "привет, мир"
    assert normalize_sequence("2 3 1") == "231"
