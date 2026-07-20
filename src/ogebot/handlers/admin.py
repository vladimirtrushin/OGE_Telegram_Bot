"""Admin-only commands: reload the task bank and view basic stats."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ogebot.config import Settings
from ogebot.db.models import Subject, User, Variant
from ogebot.repositories.users import UserRepository
from ogebot.services.loader import load_directory

router = Router(name="admin")


@router.message(Command("reload"))
async def cmd_reload(
    message: Message, user: User, session: AsyncSession, settings: Settings
) -> None:
    if not user.is_admin:
        return  # silently ignore for non-admins
    count = await load_directory(session, settings.data_dir)
    await message.answer(
        f"♻️ Перезагружено вариантов: <b>{count}</b> из <code>{settings.data_dir}</code>"
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message, user: User, session: AsyncSession) -> None:
    if not user.is_admin:
        return
    users = await UserRepository(session).count()
    subjects = await session.scalar(select(func.count()).select_from(Subject)) or 0
    variants = await session.scalar(select(func.count()).select_from(Variant)) or 0
    await message.answer(
        "📊 <b>Статистика</b>\n"
        f"Пользователей: {users}\n"
        f"Предметов: {subjects}\n"
        f"Вариантов: {variants}"
    )
