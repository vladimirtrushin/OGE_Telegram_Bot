"""Pure answer-checking logic.

This module has **no framework or database dependencies** on purpose: it is the
heart of the bot and must be trivially unit-testable. Handlers and services call
:func:`check_answer` with plain data.
"""

from __future__ import annotations

import re
import unicodedata

from ogebot.db.models import AnswerType

_WHITESPACE_RE = re.compile(r"\s+")
_TRAILING_PUNCT_RE = re.compile(r"[.,;:!?)\]}\s]+$")
_LEADING_PUNCT_RE = re.compile(r"^[(\[{\s]+")


def _normalize_common(value: str) -> str:
    """Shared normalisation: Unicode NFKC, unify comma decimal separator, trim."""
    value = unicodedata.normalize("NFKC", value)
    value = value.replace(" ", " ")  # non-breaking space -> space
    return value.strip()


def normalize_text(value: str) -> str:
    """Normalise free text for comparison (case-insensitive, spacing-tolerant)."""
    value = _normalize_common(value).casefold()
    value = value.replace("ё", "е")  # treat ё/е as equal (common in Russian)
    value = _LEADING_PUNCT_RE.sub("", value)
    value = _TRAILING_PUNCT_RE.sub("", value)
    value = _WHITESPACE_RE.sub(" ", value)
    return value


def normalize_sequence(value: str) -> str:
    """Normalise an ordered token sequence, e.g. "2 3 1" -> "231".

    Order matters (used for answer sequences and binary/number strings), but any
    spaces, commas or separators between the tokens are ignored.
    """
    value = _normalize_common(value).casefold()
    return re.sub(r"[\s,;.\-]+", "", value)


def _to_number(value: str) -> float | None:
    """Parse a number, accepting comma as a decimal separator. None if invalid."""
    cleaned = _normalize_common(value).replace(" ", "").replace(",", ".")
    if cleaned == "":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _matches_number(
    user: str, reference: str, *, rel_tol: float = 1e-9, abs_tol: float = 1e-9
) -> bool:
    user_num = _to_number(user)
    ref_num = _to_number(reference)
    if user_num is None or ref_num is None:
        # Fall back to sequence comparison if either side is not numeric.
        return normalize_sequence(user) == normalize_sequence(reference)
    diff = abs(user_num - ref_num)
    return diff <= max(abs_tol, rel_tol * abs(ref_num))


def check_answer(user_answer: str, accepted_answers: list[str], answer_type: AnswerType) -> bool:
    """Return True if ``user_answer`` matches any of the accepted answers.

    Args:
        user_answer: Raw text the student sent.
        accepted_answers: One or more reference answers (any match counts).
        answer_type: How to compare the answers.
    """
    if user_answer is None:
        return False

    for reference in accepted_answers:
        if answer_type is AnswerType.NUMBER:
            if _matches_number(user_answer, reference):
                return True
        elif answer_type is AnswerType.SEQUENCE:
            if normalize_sequence(user_answer) == normalize_sequence(reference):
                return True
        else:  # AnswerType.TEXT
            if normalize_text(user_answer) == normalize_text(reference):
                return True
    return False
