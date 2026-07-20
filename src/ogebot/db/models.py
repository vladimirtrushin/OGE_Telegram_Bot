"""ORM models describing users, the task bank and exam attempts.

Domain overview
---------------
``Subject`` (e.g. Informatics) has many ``Variant`` rows (one per month / sitting).
Each ``Variant`` holds an ordered list of ``Task`` rows (Part 1, short-answer).
When a student starts a variant an ``Attempt`` is created; every answer they send
is stored as a ``Submission`` linked to both the attempt and the task.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ogebot.db.base import Base, TimestampMixin


class AnswerType(enum.StrEnum):
    """How a student's answer is compared to the reference answer."""

    NUMBER = "number"  # numeric comparison (int/float, tolerant)
    TEXT = "text"  # normalised case-insensitive text
    SEQUENCE = "sequence"  # exact ordered token sequence, e.g. "231", "11011"


class AttemptStatus(enum.StrEnum):
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    ABANDONED = "abandoned"


# Reusable, cross-database Enum columns (stored as VARCHAR, not native enums).
_answer_type_col = Enum(AnswerType, native_enum=False, length=16, validate_strings=True)
_attempt_status_col = Enum(AttemptStatus, native_enum=False, length=16, validate_strings=True)


class User(Base, TimestampMixin):
    """A Telegram user. The Telegram user id doubles as the primary key."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str | None] = mapped_column(String(255))
    grade: Mapped[str | None] = mapped_column(String(16))  # school class, e.g. "9А"
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_registered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    attempts: Mapped[list[Attempt]] = relationship(back_populates="user")


class Subject(Base, TimestampMixin):
    """An exam subject, e.g. Informatics or Mathematics."""

    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # "informatics"
    title: Mapped[str] = mapped_column(String(128))  # "Информатика"

    variants: Mapped[list[Variant]] = relationship(
        back_populates="subject", order_by="Variant.month"
    )


class Variant(Base, TimestampMixin):
    """One exam variant (a specific paper), grouped by month/sitting."""

    __tablename__ = "variants"
    __table_args__ = (UniqueConstraint("subject_id", "slug", name="uq_variant_subject_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(String(64), index=True)  # unique per subject, e.g. "2026-09"
    month: Mapped[str] = mapped_column(String(32))  # human label, e.g. "Сентябрь 2026"
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    subject: Mapped[Subject] = relationship(back_populates="variants")
    tasks: Mapped[list[Task]] = relationship(
        back_populates="variant",
        order_by="Task.number",
        cascade="all, delete-orphan",
    )

    @property
    def task_count(self) -> int:
        return len(self.tasks)


class Task(Base, TimestampMixin):
    """A single short-answer task from Part 1 of a variant.

    Images are supported in two officially recommended ways:
      * ``image_url`` — a link to external object storage (S3/MinIO, a CDN, etc.);
      * ``image_file_id`` — a Telegram ``file_id`` cached after the first upload,
        which lets the bot resend the photo instantly without re-downloading it.
    """

    __tablename__ = "tasks"
    __table_args__ = (UniqueConstraint("variant_id", "number", name="uq_task_variant_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(Integer)  # position within the variant (1..N)
    statement: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(1024))
    image_file_id: Mapped[str | None] = mapped_column(String(256))
    answer_type: Mapped[AnswerType] = mapped_column(
        _answer_type_col, default=AnswerType.TEXT, nullable=False
    )
    # Reference answer. Multiple accepted variants are stored joined by "|".
    answer: Mapped[str] = mapped_column(String(512))
    max_score: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)

    variant: Mapped[Variant] = relationship(back_populates="tasks")

    @property
    def accepted_answers(self) -> list[str]:
        return [part for part in self.answer.split("|") if part != ""]


class Attempt(Base, TimestampMixin):
    """A student's run through a single variant."""

    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id", ondelete="CASCADE"))
    status: Mapped[AttemptStatus] = mapped_column(
        _attempt_status_col, default=AttemptStatus.IN_PROGRESS, nullable=False, index=True
    )
    current_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column()

    user: Mapped[User] = relationship(back_populates="attempts")
    variant: Mapped[Variant] = relationship()
    submissions: Mapped[list[Submission]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )


class Submission(Base, TimestampMixin):
    """A single answer submitted within an attempt."""

    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("attempt_id", "task_id", name="uq_submission_attempt_task"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), index=True
    )
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    user_answer: Mapped[str] = mapped_column(String(512))
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    attempt: Mapped[Attempt] = relationship(back_populates="submissions")
    task: Mapped[Task] = relationship()
