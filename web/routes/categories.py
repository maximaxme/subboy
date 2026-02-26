from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import Category, User
from database.db_helper import db_helper
from web.deps import get_db, get_current_user
from web.schemas import CategoryCreate, CategoryOut

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
async def list_categories(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Category).where(Category.user_id == user.id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=CategoryOut)
async def create_category(
    body: CategoryCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    cat = Category(user_id=user.id, name=body.name)
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    return cat


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Category).where(Category.id == category_id, Category.user_id == user.id)
    result = await session.execute(stmt)
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    await session.delete(cat)
    await session.commit()
    return {"ok": True}
