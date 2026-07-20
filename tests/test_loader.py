"""Tests for the YAML loader: parsing, validation and DB round-trip."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from ogebot.db.models import AnswerType
from ogebot.repositories.catalog import CatalogRepository
from ogebot.services.loader import VariantSpec, load_variant, parse_variant_file

SAMPLE_YAML = """
subject: informatics
subject_title: Информатика
slug: "2026-09"
month: Сентябрь 2026
title: Тестовый вариант
description: demo
published: true
tasks:
  - number: 1
    statement: Вопрос 1
    answer_type: number
    answer: 60
  - number: 2
    statement: Вопрос 2
    answer_type: text
    answer: [Москва, Питер]
"""


def _write(tmp_path, text: str):
    path = tmp_path / "2026-09.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_parse_and_answer_join(tmp_path) -> None:
    spec = parse_variant_file(_write(tmp_path, SAMPLE_YAML))
    assert isinstance(spec, VariantSpec)
    assert spec.subject == "informatics"
    assert spec.tasks[0].answer_type is AnswerType.NUMBER
    # A list of accepted answers is stored joined by "|".
    assert spec.tasks[1].answer == "Москва|Питер"


def test_slug_defaults_to_filename(tmp_path) -> None:
    text = SAMPLE_YAML.replace('slug: "2026-09"\n', "")
    spec = parse_variant_file(_write(tmp_path, text))
    assert spec.slug == "2026-09"


def test_duplicate_task_numbers_rejected(tmp_path) -> None:
    bad = SAMPLE_YAML.replace("number: 2", "number: 1")
    with pytest.raises(ValidationError):
        parse_variant_file(_write(tmp_path, bad))


@pytest.mark.asyncio
async def test_load_variant_roundtrip(session: AsyncSession, tmp_path) -> None:
    spec = parse_variant_file(_write(tmp_path, SAMPLE_YAML))
    await load_variant(session, spec)
    await session.commit()

    catalog = CatalogRepository(session)
    subject = await catalog.get_subject_by_code("informatics")
    assert subject is not None
    variant = await catalog.get_variant_by_slug(subject.id, "2026-09")
    assert variant is not None
    assert await catalog.count_tasks(variant.id) == 2

    task2 = await catalog.get_task_by_number(variant.id, 2)
    assert task2.accepted_answers == ["Москва", "Питер"]


@pytest.mark.asyncio
async def test_reload_replaces_tasks(session: AsyncSession, tmp_path) -> None:
    spec = parse_variant_file(_write(tmp_path, SAMPLE_YAML))
    await load_variant(session, spec)
    await session.commit()

    # Reload with a single task -> the old two tasks must be gone.
    smaller = VariantSpec.model_validate(
        {
            "subject": "informatics",
            "subject_title": "Информатика",
            "slug": "2026-09",
            "month": "Сентябрь 2026",
            "title": "Обновлённый вариант",
            "tasks": [{"number": 1, "statement": "Только одно", "answer": "1"}],
        }
    )
    await load_variant(session, smaller)
    await session.commit()

    catalog = CatalogRepository(session)
    subject = await catalog.get_subject_by_code("informatics")
    variant = await catalog.get_variant_by_slug(subject.id, "2026-09")
    assert variant.title == "Обновлённый вариант"
    assert await catalog.count_tasks(variant.id) == 1
