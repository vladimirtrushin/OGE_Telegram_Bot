"""aiogram middlewares: database session + user resolution."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ogebot.config import Settings
from ogebot.logging import get_logger
from ogebot.repositories.users import UserRepository

log = get_logger(__name__)


class DbSessionMiddleware(BaseMiddleware):
    """Open one database session per update; commit on success, rollback on error.

    The session is injected into handler data as ``session``.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.session_factory() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
            except Exception:
                await session.rollback()
                raise
            else:
                await session.commit()
                return result


class UserMiddleware(BaseMiddleware):
    """Resolve (and lazily create) the ``User`` for the current Telegram user.

    Injects ``user`` (the ORM ``User``) into handler data. Requires the session
    middleware to have run first.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        if tg_user is None or tg_user.is_bot:
            return await handler(event, data)

        session: AsyncSession = data["session"]
        users = UserRepository(session)
        user = await users.get_or_create(
            tg_user.id,
            username=tg_user.username,
            full_name=tg_user.full_name,
            is_admin=self.settings.is_admin(tg_user.id),
        )
        data["user"] = user
        return await handler(event, data)
