"""
services/user_service.py — User registration and retrieval.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str],
    first_name: Optional[str],
) -> User:
    """
    Retrieve an existing user or create a new one.
    Sets `user.is_new = True` if the user was just created.
    """
    user = await session.get(User, telegram_id)
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user.is_new = True  # transient flag
    else:
        user.is_new = False
    return user
