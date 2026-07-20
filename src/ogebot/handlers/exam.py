"""The exam flow: start a variant, answer tasks, get graded, see results."""

from __future__ import annotations

import contextlib

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from ogebot import keyboards, texts
from ogebot.config import Settings
from ogebot.db.models import AttemptStatus, Task, User
from ogebot.keyboards import ExamCB, StartCB
from ogebot.logging import get_logger
from ogebot.services.exam import Attempt, ExamService
from ogebot.states import Solving

router = Router(name="exam")
log = get_logger(__name__)


async def _send_task(message: Message, task: Task, total: int, attempt_id: int) -> None:
    """Render one task, sending its image as a photo when present."""
    text = texts.task_message(task, total)
    kb = keyboards.task_keyboard(attempt_id, task.number, is_last=task.number >= total)
    if task.image_file_id:
        await message.answer_photo(task.image_file_id, caption=text, reply_markup=kb)
        return
    if task.image_url:
        try:
            await message.answer_photo(task.image_url, caption=text, reply_markup=kb)
            return
        except Exception as exc:  # noqa: BLE001 - Telegram may fail to fetch the URL
            log.warning("photo_send_failed", url=task.image_url, error=str(exc))
            text = f"{text}\n\n🖼 Изображение: {task.image_url}"
    await message.answer(text, reply_markup=kb)


async def _finish_and_show(
    message: Message, exam: ExamService, attempt: Attempt, state: FSMContext
) -> None:
    await exam.finish(attempt)
    submissions = await exam.attempts.list_submissions(attempt.id)
    variant = await exam.catalog.get_variant(attempt.variant_id)
    await state.clear()
    await message.answer(texts.results(attempt, variant, submissions))


async def _load_active_attempt(exam: ExamService, attempt_id: int | None) -> Attempt | None:
    if attempt_id is None:
        return None
    attempt = await exam.attempts.get(attempt_id)
    if attempt is None or attempt.status is not AttemptStatus.IN_PROGRESS:
        return None
    return attempt


@router.callback_query(StartCB.filter())
async def on_start_variant(
    callback: CallbackQuery,
    callback_data: StartCB,
    user: User,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    exam = ExamService(session)
    variant = await exam.catalog.get_variant(callback_data.variant_id)
    if variant is None:
        await callback.answer("Вариант не найден", show_alert=True)
        return
    total = await exam.catalog.count_tasks(variant.id)
    if total == 0:
        await callback.answer("В этом варианте пока нет заданий", show_alert=True)
        return

    attempt = await exam.start(user.id, variant)
    await state.set_state(Solving.answering)
    await state.update_data(attempt_id=attempt.id)

    first_task = await exam.get_task(variant.id, attempt.current_number)
    await callback.message.answer(
        f"▶️ Начинаем: <b>{variant.title}</b>. Удачи! Отправляй ответы текстом."
    )
    await _send_task(callback.message, first_task, total, attempt.id)
    await callback.answer()


@router.message(Solving.answering, F.text)
async def on_answer(
    message: Message, state: FSMContext, session: AsyncSession, settings: Settings
) -> None:
    exam = ExamService(session)
    data = await state.get_data()
    attempt = await _load_active_attempt(exam, data.get("attempt_id"))
    if attempt is None:
        await state.clear()
        await message.answer("Сессия истекла. Нажми /menu, чтобы выбрать вариант заново.")
        return

    total = attempt.max_score
    task = await exam.get_task(attempt.variant_id, attempt.current_number)
    if task is None:
        await _finish_and_show(message, exam, attempt, state)
        return

    result = await exam.submit(attempt, task, message.text)
    show_correct = settings.immediate_feedback
    feedback_text = texts.feedback(
        is_correct=result.is_correct,
        user_answer=message.text.strip(),
        correct_answer=result.correct_answer,
        show_correct=show_correct,
    )
    feedback_kb = (
        keyboards.explanation_keyboard(attempt.id, task.number)
        if result.explanation and show_correct
        else None
    )
    await message.answer(feedback_text, reply_markup=feedback_kb)

    if result.is_last:
        await _finish_and_show(message, exam, attempt, state)
    else:
        next_task = await exam.get_task(attempt.variant_id, result.next_number)
        await _send_task(message, next_task, total, attempt.id)


@router.message(Solving.answering)
async def on_non_text_answer(message: Message) -> None:
    await message.answer("Пожалуйста, отправь ответ <b>текстом</b>.")


@router.callback_query(ExamCB.filter(F.action == "skip"))
async def on_skip(
    callback: CallbackQuery, callback_data: ExamCB, state: FSMContext, session: AsyncSession
) -> None:
    exam = ExamService(session)
    attempt = await _load_active_attempt(exam, callback_data.attempt_id)
    if attempt is None:
        await callback.answer("Эта сессия уже завершена", show_alert=True)
        return

    total = attempt.max_score
    next_number = callback_data.number + 1
    if attempt.current_number <= callback_data.number:
        attempt.current_number = next_number
    await session.flush()

    await _clear_markup(callback)
    await callback.answer("Пропущено")
    if next_number > total:
        await _finish_and_show(callback.message, exam, attempt, state)
    else:
        next_task = await exam.get_task(attempt.variant_id, next_number)
        await _send_task(callback.message, next_task, total, attempt.id)


@router.callback_query(ExamCB.filter(F.action == "finish"))
async def on_finish(
    callback: CallbackQuery, callback_data: ExamCB, state: FSMContext, session: AsyncSession
) -> None:
    exam = ExamService(session)
    attempt = await _load_active_attempt(exam, callback_data.attempt_id)
    if attempt is None:
        await callback.answer("Эта сессия уже завершена", show_alert=True)
        return
    await _clear_markup(callback)
    await _finish_and_show(callback.message, exam, attempt, state)
    await callback.answer()


@router.callback_query(ExamCB.filter(F.action == "explain"))
async def on_explain(callback: CallbackQuery, callback_data: ExamCB, session: AsyncSession) -> None:
    exam = ExamService(session)
    attempt = await exam.attempts.get(callback_data.attempt_id)
    if attempt is None:
        await callback.answer()
        return
    task = await exam.get_task(attempt.variant_id, callback_data.number)
    if task and task.explanation:
        await callback.message.answer(texts.explanation(task.explanation))
    await callback.answer()


async def _clear_markup(callback: CallbackQuery) -> None:
    """Remove inline buttons from a message; ignore 'message not modified' errors."""
    with contextlib.suppress(Exception):  # best-effort cleanup
        await callback.message.edit_reply_markup(reply_markup=None)
