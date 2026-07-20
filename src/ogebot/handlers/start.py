"""Onboarding: /start, lightweight registration ("login"), menu, profile, help."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from ogebot import texts
from ogebot.db.models import User
from ogebot.handlers.catalog import show_subjects
from ogebot.repositories.attempts import AttemptRepository
from ogebot.repositories.users import UserRepository
from ogebot.states import Registration

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, user: User, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    if user.is_registered:
        await message.answer(texts.WELCOME_BACK.format(name=user.full_name or "ученик"))
        await show_subjects(message, session)
        return
    await message.answer(texts.WELCOME_NEW.format(name=texts.BOT_NAME))
    await state.set_state(Registration.waiting_for_name)


@router.message(Registration.waiting_for_name, F.text)
async def registration_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Имя слишком короткое. Напиши, пожалуйста, имя и фамилию.")
        return
    await state.update_data(full_name=name)
    await state.set_state(Registration.waiting_for_grade)
    await message.answer(texts.ASK_GRADE.format(name=name.split()[0]))


@router.message(Registration.waiting_for_grade, Command("skip"))
async def registration_skip_grade(
    message: Message, state: FSMContext, user: User, session: AsyncSession
) -> None:
    await _finish_registration(message, state, user, session, grade=None)


@router.message(Registration.waiting_for_grade, F.text)
async def registration_grade(
    message: Message, state: FSMContext, user: User, session: AsyncSession
) -> None:
    grade = message.text.strip()
    await _finish_registration(message, state, user, session, grade=grade)


async def _finish_registration(
    message: Message,
    state: FSMContext,
    user: User,
    session: AsyncSession,
    *,
    grade: str | None,
) -> None:
    data = await state.get_data()
    full_name = data.get("full_name") or user.full_name or "ученик"
    users = UserRepository(session)
    await users.complete_registration(user, full_name, grade)
    await state.clear()
    await message.answer(texts.REGISTERED)
    await show_subjects(message, session)


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await show_subjects(message, session)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.HELP.format(name=texts.BOT_NAME))


@router.message(Command("profile"))
async def cmd_profile(message: Message, user: User, session: AsyncSession) -> None:
    attempts = await AttemptRepository(session).recent_finished(user.id, limit=10)
    await message.answer(texts.profile(user.full_name, user.grade, attempts))
