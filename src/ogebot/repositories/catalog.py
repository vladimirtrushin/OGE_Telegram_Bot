"""Read/write access to the task bank: subjects, variants and tasks."""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ogebot.db.models import Subject, Task, Variant


class CatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- Subjects ---
    async def list_subjects(self) -> list[Subject]:
        result = await self.session.scalars(select(Subject).order_by(Subject.title))
        return list(result.all())

    async def get_subject(self, subject_id: int) -> Subject | None:
        return await self.session.get(Subject, subject_id)

    async def get_subject_by_code(self, code: str) -> Subject | None:
        return await self.session.scalar(select(Subject).where(Subject.code == code))

    async def upsert_subject(self, code: str, title: str) -> Subject:
        subject = await self.get_subject_by_code(code)
        if subject is None:
            subject = Subject(code=code, title=title)
            self.session.add(subject)
            await self.session.flush()
        else:
            subject.title = title
        return subject

    # --- Variants ---
    async def list_variants(self, subject_id: int, *, published_only: bool = True) -> list[Variant]:
        stmt = select(Variant).where(Variant.subject_id == subject_id)
        if published_only:
            stmt = stmt.where(Variant.is_published.is_(True))
        stmt = stmt.order_by(Variant.slug)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_variant(self, variant_id: int) -> Variant | None:
        return await self.session.get(Variant, variant_id)

    async def get_variant_with_tasks(self, variant_id: int) -> Variant | None:
        stmt = select(Variant).where(Variant.id == variant_id).options(selectinload(Variant.tasks))
        return await self.session.scalar(stmt)

    async def get_variant_by_slug(self, subject_id: int, slug: str) -> Variant | None:
        stmt = select(Variant).where(Variant.subject_id == subject_id, Variant.slug == slug)
        return await self.session.scalar(stmt)

    async def count_tasks(self, variant_id: int) -> int:
        return (
            await self.session.scalar(
                select(func.count()).select_from(Task).where(Task.variant_id == variant_id)
            )
            or 0
        )

    async def get_task_by_number(self, variant_id: int, number: int) -> Task | None:
        stmt = select(Task).where(Task.variant_id == variant_id, Task.number == number)
        return await self.session.scalar(stmt)

    # --- Bulk replace (used by the seed loader) ---
    async def replace_variant(
        self,
        subject: Subject,
        slug: str,
        *,
        month: str,
        title: str,
        description: str | None,
        is_published: bool,
    ) -> Variant:
        """Create or reset a variant, clearing its existing tasks."""
        variant = await self.get_variant_by_slug(subject.id, slug)
        if variant is None:
            variant = Variant(subject_id=subject.id, slug=slug)
            self.session.add(variant)
        else:
            # Remove existing tasks so the variant can be re-seeded cleanly.
            await self.session.execute(delete(Task).where(Task.variant_id == variant.id))
        variant.month = month
        variant.title = title
        variant.description = description
        variant.is_published = is_published
        await self.session.flush()
        return variant
