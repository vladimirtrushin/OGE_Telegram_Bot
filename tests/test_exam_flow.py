"""Integration test for the exam service: start → answer → score."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ogebot.db.models import AttemptStatus
from ogebot.repositories.users import UserRepository
from ogebot.services.exam import ExamService
from ogebot.services.loader import VariantSpec, load_variant

VARIANT = {
    "subject": "informatics",
    "subject_title": "Информатика",
    "slug": "test",
    "month": "Тест",
    "title": "Мини-вариант",
    "tasks": [
        {"number": 1, "statement": "2+2?", "answer_type": "number", "answer": "4"},
        {"number": 2, "statement": "Столица России?", "answer_type": "text", "answer": "Москва"},
        {"number": 3, "statement": "27 в двоичной?", "answer_type": "sequence", "answer": "11011"},
    ],
}


async def _setup(session: AsyncSession):
    await load_variant(session, VariantSpec.model_validate(VARIANT))
    user = await UserRepository(session).get_or_create(123, username="stud", full_name="Тест")
    await session.flush()
    exam = ExamService(session)
    subject = await exam.catalog.get_subject_by_code("informatics")
    variant = await exam.catalog.get_variant_by_slug(subject.id, "test")
    return exam, user, variant


@pytest.mark.asyncio
async def test_full_correct_run(session: AsyncSession) -> None:
    exam, user, variant = await _setup(session)
    attempt = await exam.start(user.id, variant)
    assert attempt.max_score == 3

    answers = {1: "4", 2: " москва ", 3: "1 10 11"}
    result = None
    for _ in range(3):
        task = await exam.get_task(attempt.variant_id, attempt.current_number)
        result = await exam.submit(attempt, task, answers[task.number])
        assert result.is_correct is True
    assert result is not None and result.is_last is True

    await exam.finish(attempt)
    assert attempt.status is AttemptStatus.FINISHED
    assert attempt.score == 3


@pytest.mark.asyncio
async def test_partial_and_reanswer(session: AsyncSession) -> None:
    exam, user, variant = await _setup(session)
    attempt = await exam.start(user.id, variant)

    task1 = await exam.get_task(attempt.variant_id, 1)
    await exam.submit(attempt, task1, "5")  # wrong
    assert attempt.score == 0

    # Re-answer task 1 correctly: score must not double-count.
    await exam.submit(attempt, task1, "4")
    assert attempt.score == 1

    submissions = await exam.attempts.list_submissions(attempt.id)
    assert len(submissions) == 1  # still a single submission row for task 1
    assert submissions[0].is_correct is True


@pytest.mark.asyncio
async def test_abandon_previous_attempt(session: AsyncSession) -> None:
    exam, user, variant = await _setup(session)
    first = await exam.start(user.id, variant)
    second = await exam.start(user.id, variant)

    refreshed_first = await exam.attempts.get(first.id)
    assert refreshed_first.status is AttemptStatus.ABANDONED
    assert second.status is AttemptStatus.IN_PROGRESS
