"""Catalog navigation: pick a subject, then a month/variant, then start."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from ogebot import texts
from ogebot.keyboards import (
    BackCB,
    SubjectCB,
    VariantCB,
    subjects_keyboard,
    variant_card_keyboard,
    variants_keyboard,
)
from ogebot.repositories.catalog import CatalogRepository

router = Router(name="catalog")


async def render_subjects(session: AsyncSession) -> tuple[str, InlineKeyboardMarkup | None]:
    catalog = CatalogRepository(session)
    subjects = await catalog.list_subjects()
    if not subjects:
        return texts.NO_SUBJECTS, None
    return texts.CHOOSE_SUBJECT, subjects_keyboard(subjects)


async def show_subjects(message: Message, session: AsyncSession) -> None:
    text, markup = await render_subjects(session)
    await message.answer(text, reply_markup=markup)


@router.callback_query(SubjectCB.filter())
async def on_subject_chosen(
    callback: CallbackQuery, callback_data: SubjectCB, session: AsyncSession
) -> None:
    catalog = CatalogRepository(session)
    subject = await catalog.get_subject(callback_data.subject_id)
    if subject is None:
        await callback.answer("Предмет не найден", show_alert=True)
        return
    variants = await catalog.list_variants(subject.id)
    if not variants:
        await callback.message.edit_text(texts.NO_VARIANTS)
        await callback.answer()
        return
    await callback.message.edit_text(
        texts.CHOOSE_VARIANT.format(subject=subject.title),
        reply_markup=variants_keyboard(subject.id, variants),
    )
    await callback.answer()


@router.callback_query(VariantCB.filter())
async def on_variant_chosen(
    callback: CallbackQuery, callback_data: VariantCB, session: AsyncSession
) -> None:
    catalog = CatalogRepository(session)
    variant = await catalog.get_variant(callback_data.variant_id)
    if variant is None:
        await callback.answer("Вариант не найден", show_alert=True)
        return
    task_count = await catalog.count_tasks(variant.id)
    await callback.message.edit_text(
        texts.variant_card(variant, task_count),
        reply_markup=variant_card_keyboard(variant.subject_id, variant.id),
    )
    await callback.answer()


@router.callback_query(BackCB.filter(F.to == "subjects"))
async def on_back_to_subjects(callback: CallbackQuery, session: AsyncSession) -> None:
    text, markup = await render_subjects(session)
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(BackCB.filter(F.to == "variants"))
async def on_back_to_variants(
    callback: CallbackQuery, callback_data: BackCB, session: AsyncSession
) -> None:
    catalog = CatalogRepository(session)
    subject = await catalog.get_subject(callback_data.subject_id)
    if subject is None:
        text, markup = await render_subjects(session)
        await callback.message.edit_text(text, reply_markup=markup)
        await callback.answer()
        return
    variants = await catalog.list_variants(subject.id)
    await callback.message.edit_text(
        texts.CHOOSE_VARIANT.format(subject=subject.title),
        reply_markup=variants_keyboard(subject.id, variants),
    )
    await callback.answer()
