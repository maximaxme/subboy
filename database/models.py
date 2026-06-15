from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, ForeignKey, Numeric, Date, Boolean, DateTime, func
from datetime import date, datetime
from decimal import Decimal

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String)
    full_name: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    categories: Mapped[list["Category"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    settings: Mapped["NotificationSettings"] = relationship(back_populates="user", cascade="all, delete-orphan")

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String)

    user: Mapped["User"] = relationship(back_populates="categories")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="category")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    price_currency: Mapped[str] = mapped_column(String, default="RUB", server_default="RUB")
    price_original: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    period: Mapped[str] = mapped_column(String) # 'monthly', 'yearly'
    next_payment: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # When True, the "still using this?" question before a charge is skipped
    # (for subscriptions you always keep, e.g. Yandex Music).
    always_keep: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    user: Mapped["User"] = relationship(back_populates="subscriptions")
    category: Mapped["Category"] = relationship(back_populates="subscriptions")

class Payment(Base):
    """A single charge that occurred for a subscription.

    Logged automatically when a subscription's next_payment date passes. Fields are
    denormalised (name/amount/currency snapshot) so history survives a subscription
    being renamed or deleted.
    """
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String, default="RUB", server_default="RUB")
    amount_original: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    paid_on: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    day_before: Mapped[bool] = mapped_column(Boolean, default=True)
    weekly: Mapped[bool] = mapped_column(Boolean, default=True)
    monthly: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="settings")
