"""Load task banks from YAML files into the database.

File format (``data/variants/<subject>/<slug>.yaml``)::

    subject: informatics          # stable code, used as the DB key
    subject_title: Информатика
    slug: "2026-09"               # optional; defaults to the file name
    month: Сентябрь 2026
    title: "Информатика ОГЭ — сентябрь 2026"
    description: Тренировочный вариант первой части.
    published: true
    tasks:
      - number: 1
        statement: "Условие задания..."
        answer_type: number        # number | text | sequence
        answer: 60                  # single value, or a list of accepted values
        image_url: null            # optional link to storage
        explanation: "Разбор..."   # optional

The loader is idempotent: re-running it fully replaces the tasks of a variant,
so editing a YAML file and re-seeding always yields a clean, up-to-date variant.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from ogebot.db.models import AnswerType, Task
from ogebot.logging import get_logger
from ogebot.repositories.catalog import CatalogRepository

log = get_logger(__name__)


class TaskSpec(BaseModel):
    number: int = Field(ge=1)
    statement: str
    answer_type: AnswerType = AnswerType.TEXT
    answer: str
    image_url: str | None = None
    image_file_id: str | None = None
    max_score: int = Field(default=1, ge=1)
    explanation: str | None = None

    @field_validator("answer", mode="before")
    @classmethod
    def _coerce_answer(cls, value: object) -> str:
        """Accept a scalar or a list of accepted answers; store joined by "|"."""
        if isinstance(value, list):
            return "|".join(str(item) for item in value)
        return str(value)


class VariantSpec(BaseModel):
    subject: str
    subject_title: str
    slug: str
    month: str
    title: str
    description: str | None = None
    published: bool = True
    tasks: list[TaskSpec]

    @field_validator("tasks")
    @classmethod
    def _unique_numbers(cls, tasks: list[TaskSpec]) -> list[TaskSpec]:
        numbers = [t.number for t in tasks]
        if len(numbers) != len(set(numbers)):
            raise ValueError("task numbers must be unique within a variant")
        return tasks


def parse_variant_file(path: Path) -> VariantSpec:
    """Parse and validate a single variant YAML file."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw.setdefault("slug", path.stem)
    return VariantSpec.model_validate(raw)


def discover_variant_files(data_dir: Path) -> list[Path]:
    """Return all variant YAML files under ``data_dir`` (recursively, sorted)."""
    return sorted(p for p in data_dir.rglob("*.yaml") if p.is_file())


async def load_variant(session: AsyncSession, spec: VariantSpec) -> None:
    """Upsert a single variant (and its tasks) into the database."""
    catalog = CatalogRepository(session)
    subject = await catalog.upsert_subject(spec.subject, spec.subject_title)
    variant = await catalog.replace_variant(
        subject,
        spec.slug,
        month=spec.month,
        title=spec.title,
        description=spec.description,
        is_published=spec.published,
    )
    for task_spec in spec.tasks:
        session.add(
            Task(
                variant_id=variant.id,
                number=task_spec.number,
                statement=task_spec.statement,
                answer_type=task_spec.answer_type,
                answer=task_spec.answer,
                image_url=task_spec.image_url,
                image_file_id=task_spec.image_file_id,
                max_score=task_spec.max_score,
                explanation=task_spec.explanation,
            )
        )
    await session.flush()


async def load_directory(session: AsyncSession, data_dir: Path) -> int:
    """Load every variant file under ``data_dir``. Returns the number loaded."""
    files = discover_variant_files(data_dir)
    if not files:
        log.warning("no_variant_files_found", data_dir=str(data_dir))
        return 0
    count = 0
    for path in files:
        try:
            spec = parse_variant_file(path)
        except Exception as exc:  # noqa: BLE001 - report which file failed and continue
            log.error("variant_parse_failed", file=str(path), error=str(exc))
            continue
        await load_variant(session, spec)
        count += 1
        log.info(
            "variant_loaded",
            file=str(path),
            subject=spec.subject,
            slug=spec.slug,
            tasks=len(spec.tasks),
        )
    return count
