from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta

from database.db_helper import db_helper
from web.auth_telegram import verify_telegram_login
from services.user_service import get_or_create_user
from config import config

router = APIRouter(prefix="/auth", tags=["auth"])


def _jwt_secret() -> str:
    if config.JWT_SECRET:
        return config.JWT_SECRET
    return config.BOT_TOKEN.get_secret_value()


class TelegramLoginBody(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


@router.post("/telegram")
async def login_telegram(body: TelegramLoginBody):
    """Вход через Telegram Login Widget. Возвращает JWT для API."""
    ok = verify_telegram_login(
        body.hash,
        id=body.id,
        first_name=body.first_name,
        last_name=body.last_name,
        username=body.username,
        photo_url=body.photo_url,
        auth_date=body.auth_date,
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Неверные данные от Telegram")
    async with db_helper.session_factory() as session:
        full_name = (body.first_name or "") + (" " + (body.last_name or "")).strip()
        user = await get_or_create_user(
            session, body.id, username=body.username, full_name=full_name or None
        )
    payload = {
        "sub": str(user.id),
        "exp": datetime.utcnow() + timedelta(days=30),
    }
    token = jwt.encode(payload, _jwt_secret(), algorithm="HS256")
    return {"access_token": token, "user_id": user.id}


class DevLoginBody(BaseModel):
    user_id: int


@router.post("/dev-login")
async def dev_login(body: DevLoginBody, request: Request):
    """
    Вход только по user_id. Работает только с localhost — для теста без HTTPS.
    Не использовать на продакшене.
    """
    host = (request.client.host if request.client else "") or request.headers.get("host", "")
    if "localhost" not in host and "127.0.0.1" not in host:
        raise HTTPException(status_code=403, detail="Доступно только с localhost")
    async with db_helper.session_factory() as session:
        user = await get_or_create_user(session, body.user_id)
    payload = {"sub": str(user.id), "exp": datetime.utcnow() + timedelta(days=30)}
    token = jwt.encode(payload, _jwt_secret(), algorithm="HS256")
    return {"access_token": token, "user_id": user.id}
