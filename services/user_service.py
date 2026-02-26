from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, NotificationSettings
from sqlalchemy import select

async def get_or_create_user(
    session: AsyncSession,
    user_id: int,
    username: str | None = None,
    full_name: str | None = None
) -> User:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=user_id,
            username=username,
            full_name=full_name
        )
        session.add(user)
        
        # Добавляем настройки уведомлений по умолчанию
        settings = NotificationSettings(user_id=user_id)
        session.add(settings)
        
        await session.commit()
    
    return user
