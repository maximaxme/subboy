from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Subscription, NotificationSettings, User
from aiogram import Bot

async def check_and_send_notifications(bot: Bot, session: AsyncSession):
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    # 1. Уведомления за день до списания
    stmt = (
        select(Subscription, User)
        .join(User)
        .join(NotificationSettings, User.id == NotificationSettings.user_id)
        .where(
            Subscription.next_payment == tomorrow,
            NotificationSettings.day_before == True
        )
    )
    result = await session.execute(stmt)
    
    for sub, user in result:
        try:
            await bot.send_message(
                chat_id=user.id,
                text=(
                    f"⏰ Завтра списание\n"
                    f"{sub.name} — {sub.price} ₽\n\n"
                    f"Проверь, нужен ли сервис 😉"
                )
            )
            # После уведомления можно обновить дату следующего списания, 
            # если списание уже завтра (или это лучше делать в день списания)
        except Exception as e:
            print(f"Ошибка отправки уведомления пользователю {user.id}: {e}")

    # Здесь можно добавить логику для еженедельных и ежемесячных отчетов
