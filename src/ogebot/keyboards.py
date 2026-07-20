"""Inline keyboards and typed callback data factories."""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ogebot.db.models import Subject, Variant


class SubjectCB(CallbackData, prefix="subj"):
    subject_id: int


class VariantCB(CallbackData, prefix="var"):
    variant_id: int


class StartCB(CallbackData, prefix="start"):
    variant_id: int


class BackCB(CallbackData, prefix="back"):
    to: str  # "subjects" | "variants"
    subject_id: int = 0


class ExamCB(CallbackData, prefix="exam"):
    action: str  # "next" | "skip" | "finish" | "explain"
    attempt_id: int
    number: int = 0


def subjects_keyboard(subjects: list[Subject]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for subject in subjects:
        builder.button(text=f"📘 {subject.title}", callback_data=SubjectCB(subject_id=subject.id))
    builder.adjust(1)
    return builder.as_markup()


def variants_keyboard(subject_id: int, variants: list[Variant]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for variant in variants:
        builder.button(
            text=f"🗓 {variant.month}",
            callback_data=VariantCB(variant_id=variant.id),
        )
    builder.button(text="⬅️ К предметам", callback_data=BackCB(to="subjects"))
    builder.adjust(1)
    return builder.as_markup()


def variant_card_keyboard(subject_id: int, variant_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Начать вариант", callback_data=StartCB(variant_id=variant_id))
    builder.button(text="⬅️ К вариантам", callback_data=BackCB(to="variants", subject_id=subject_id))
    builder.adjust(1)
    return builder.as_markup()


def explanation_keyboard(attempt_id: int, number: int) -> InlineKeyboardMarkup:
    """A single '💡 Разбор' button shown under answer feedback when a task has one."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💡 Разбор",
        callback_data=ExamCB(action="explain", attempt_id=attempt_id, number=number),
    )
    return builder.as_markup()


def task_keyboard(attempt_id: int, number: int, *, is_last: bool) -> InlineKeyboardMarkup:
    """Shown together with a task: lets the user skip or finish without answering."""
    builder = InlineKeyboardBuilder()
    if is_last:
        builder.button(
            text="🏁 Завершить",
            callback_data=ExamCB(action="finish", attempt_id=attempt_id),
        )
    else:
        builder.button(
            text="⏭ Пропустить",
            callback_data=ExamCB(action="skip", attempt_id=attempt_id, number=number),
        )
    builder.button(
        text="🚪 Выйти",
        callback_data=ExamCB(action="finish", attempt_id=attempt_id),
    )
    builder.adjust(2)
    return builder.as_markup()
