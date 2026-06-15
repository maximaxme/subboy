from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from database.models import Subscription, User
from database.db_helper import db_helper
from web.deps import get_db, get_current_user
from web.schemas import SubscriptionCreate, SubscriptionUpdate, SubscriptionOut
from decimal import Decimal

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("", response_model=list[SubscriptionOut])
async def list_subscriptions(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Subscription)
        .options(joinedload(Subscription.category))
        .where(Subscription.user_id == user.id)
    )
    result = await session.execute(stmt)
    return list(result.unique().scalars().all())


@router.post("", response_model=SubscriptionOut)
async def create_subscription(
    body: SubscriptionCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    sub = Subscription(
        user_id=user.id,
        name=body.name,
        price=Decimal(str(body.price)),
        period=body.period,
        category_id=body.category_id,
        next_payment=body.next_payment,
    )
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return sub


@router.put("/{subscription_id}", response_model=SubscriptionOut)
async def update_subscription(
    subscription_id: int,
    body: SubscriptionUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Subscription).where(
        Subscription.id == subscription_id,
        Subscription.user_id == user.id,
    )
    result = await session.execute(stmt)
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Подписка не найдена")

    update_data = body.model_dump(exclude_none=True)
    if "price" in update_data:
        update_data["price"] = Decimal(str(update_data["price"]))
    for key, value in update_data.items():
        setattr(sub, key, value)

    await session.commit()
    await session.refresh(sub)
    return sub


@router.patch("/{subscription_id}/toggle", response_model=SubscriptionOut)
async def toggle_subscription(
    subscription_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Subscription).where(
        Subscription.id == subscription_id,
        Subscription.user_id == user.id,
    )
    result = await session.execute(stmt)
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Подписка не найдена")

    sub.is_active = not sub.is_active
    await session.commit()
    await session.refresh(sub)
    return sub


@router.delete("/{subscription_id}")
async def delete_subscription(
    subscription_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Subscription).where(
        Subscription.id == subscription_id,
        Subscription.user_id == user.id,
    )
    result = await session.execute(stmt)
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    await session.delete(sub)
    await session.commit()
    return {"ok": True}
