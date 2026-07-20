"""Exam orchestration: starting attempts, grading answers, building results."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from ogebot.db.models import Attempt, Task, Variant
from ogebot.repositories.attempts import AttemptRepository
from ogebot.repositories.catalog import CatalogRepository
from ogebot.services.grading import check_answer


@dataclass(slots=True)
class SubmissionResult:
    task: Task
    is_correct: bool
    score: int
    correct_answer: str
    explanation: str | None
    is_last: bool
    next_number: int | None


class ExamService:
    """High-level operations used by the exam handlers."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.catalog = CatalogRepository(session)
        self.attempts = AttemptRepository(session)

    async def start(self, user_id: int, variant: Variant) -> Attempt:
        """Create a fresh attempt, abandoning any previous in-progress one."""
        await self.attempts.abandon_active(user_id)
        task_count = await self.catalog.count_tasks(variant.id)
        return await self.attempts.create(user_id, variant.id, max_score=task_count)

    async def get_task(self, variant_id: int, number: int) -> Task | None:
        return await self.catalog.get_task_by_number(variant_id, number)

    async def submit(self, attempt: Attempt, task: Task, user_answer: str) -> SubmissionResult:
        """Grade a single answer, persist it and advance the attempt pointer."""
        is_correct = check_answer(user_answer, task.accepted_answers, task.answer_type)
        score = task.max_score if is_correct else 0
        await self.attempts.record_submission(
            attempt, task.id, user_answer.strip(), is_correct, score
        )

        total = attempt.max_score
        is_last = task.number >= total
        next_number = None if is_last else task.number + 1
        if next_number is not None and attempt.current_number <= task.number:
            attempt.current_number = next_number
        await self.session.flush()

        return SubmissionResult(
            task=task,
            is_correct=is_correct,
            score=score,
            correct_answer=task.accepted_answers[0] if task.accepted_answers else task.answer,
            explanation=task.explanation,
            is_last=is_last,
            next_number=next_number,
        )

    async def finish(self, attempt: Attempt) -> Attempt:
        return await self.attempts.finish(attempt)
