from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from database.models import Subscription, User
from database.db_helper import db_helper
from web.deps import get_db, get_current_user
from web.schemas import ReportSummary
from decimal import Decimal

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary", response_model=ReportSummary)
async def report_summary(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Subscription)
        .options(joinedload(Subscription.category))
        .where(Subscription.user_id == user.id)
    )
    result = await session.execute(stmt)
    subscriptions = list(result.unique().scalars().all())
    total = Decimal(0)
    by_category: dict[str, float] = {}
    for sub in subscriptions:
        monthly = sub.price if sub.period == "monthly" else sub.price / 12
        total += monthly
        cat_name = sub.category.name if sub.category else "Без категории"
        by_category[cat_name] = by_category.get(cat_name, 0) + float(monthly)
    return ReportSummary(
        total_monthly=float(total),
        by_category=by_category,
    )
