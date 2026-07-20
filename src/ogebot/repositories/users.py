"""User persistence."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ogebot.db.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_or_create(
        self,
        user_id: int,
        *,
        username: str | None = None,
        full_name: str | None = None,
        is_admin: bool = False,
    ) -> User:
        user = await self.session.get(User, user_id)
        if user is None:
            user = User(
                id=user_id,
                username=username,
                full_name=full_name,
                is_admin=is_admin,
            )
            self.session.add(user)
            await self.session.flush()
        else:
            # Keep lightweight profile fields fresh on every interaction.
            if username is not None:
                user.username = username
            if is_admin and not user.is_admin:
                user.is_admin = True
        return user

    async def complete_registration(self, user: User, full_name: str, grade: str | None) -> User:
        user.full_name = full_name
        user.grade = grade
        user.is_registered = True
        await self.session.flush()
        return user

    async def count(self) -> int:
        return await self.session.scalar(select(func.count()).select_from(User)) or 0
