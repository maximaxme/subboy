from pydantic import BaseModel
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


class CategoryCreate(BaseModel):
    name: str


class CategoryOut(BaseModel):
    id: int
    user_id: int
    name: str

    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    name: str
    price: float
    period: str  # monthly | yearly
    category_id: Optional[int] = None
    next_payment: date


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    period: Optional[str] = None
    category_id: Optional[int] = None
    next_payment: Optional[date] = None
    is_active: Optional[bool] = None


class SubscriptionOut(BaseModel):
    id: int
    user_id: int
    category_id: Optional[int]
    name: str
    price: Decimal
    period: str
    next_payment: date
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ReportSummary(BaseModel):
    total_monthly: float
    by_category: dict[str, float]
