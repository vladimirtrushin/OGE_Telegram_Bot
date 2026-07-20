"""Persistence for exam attempts and per-task submissions."""

from __future__ import annotations

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ogebot.db.models import Attempt, AttemptStatus, Submission


class AttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, attempt_id: int) -> Attempt | None:
        return await self.session.get(Attempt, attempt_id)

    async def get_active(self, user_id: int) -> Attempt | None:
        """Return the user's in-progress attempt, if any."""
        stmt = (
            select(Attempt)
            .where(Attempt.user_id == user_id, Attempt.status == AttemptStatus.IN_PROGRESS)
            .order_by(desc(Attempt.created_at))
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def abandon_active(self, user_id: int) -> None:
        """Mark any in-progress attempts for the user as abandoned."""
        await self.session.execute(
            update(Attempt)
            .where(Attempt.user_id == user_id, Attempt.status == AttemptStatus.IN_PROGRESS)
            .values(status=AttemptStatus.ABANDONED)
        )

    async def create(self, user_id: int, variant_id: int, max_score: int) -> Attempt:
        attempt = Attempt(
            user_id=user_id,
            variant_id=variant_id,
            status=AttemptStatus.IN_PROGRESS,
            current_number=1,
            score=0,
            max_score=max_score,
        )
        self.session.add(attempt)
        await self.session.flush()
        return attempt

    async def get_submission(self, attempt_id: int, task_id: int) -> Submission | None:
        stmt = select(Submission).where(
            Submission.attempt_id == attempt_id, Submission.task_id == task_id
        )
        return await self.session.scalar(stmt)

    async def record_submission(
        self,
        attempt: Attempt,
        task_id: int,
        user_answer: str,
        is_correct: bool,
        score: int,
    ) -> Submission:
        """Insert or update a submission and keep the attempt score consistent."""
        submission = await self.get_submission(attempt.id, task_id)
        if submission is None:
            submission = Submission(attempt_id=attempt.id, task_id=task_id)
            self.session.add(submission)
        else:
            # Re-answering a task: subtract the old score before applying the new one.
            attempt.score -= submission.score
        submission.user_answer = user_answer
        submission.is_correct = is_correct
        submission.score = score
        attempt.score += score
        await self.session.flush()
        return submission

    async def list_submissions(self, attempt_id: int) -> list[Submission]:
        stmt = (
            select(Submission)
            .where(Submission.attempt_id == attempt_id)
            .options(selectinload(Submission.task))
            .order_by(Submission.id)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def finish(self, attempt: Attempt) -> Attempt:
        attempt.status = AttemptStatus.FINISHED
        attempt.finished_at = func.now()
        await self.session.flush()
        return attempt

    async def recent_finished(self, user_id: int, limit: int = 10) -> list[Attempt]:
        stmt = (
            select(Attempt)
            .where(Attempt.user_id == user_id, Attempt.status == AttemptStatus.FINISHED)
            .options(selectinload(Attempt.variant))
            .order_by(desc(Attempt.finished_at))
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
