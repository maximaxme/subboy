"""
services/user_service.py — User registration and lookup helpers.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import NotificationSettings, User


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    full_name: str | None,
) -> User:
    """
    Return the existing User record or create a new one.
    Also creates default NotificationSettings (day_before=True) for new users.
    """
    user = await session.get(User, telegram_id)
    if user is None:
        user = User(
            id=telegram_id,
            username=username,
            full_name=full_name,
        )
        session.add(user)

        # Default notification settings for new users
        ns = NotificationSettings(
            user_id=telegram_id,
            day_before=True,
            weekly=False,
            monthly=False,
        )
        session.add(ns)
        await session.commit()
    else:
        # Keep username/full_name up to date
        changed = False
        if user.username != username:
            user.username = username
            changed = True
        if user.full_name != full_name:
            user.full_name = full_name
            changed = True
        if changed:
            await session.commit()

    return user
