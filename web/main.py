"""
REST API для сайта subboy. Та же БД и модели, что и у бота.
Запуск: uvicorn web.main:app --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from config import config
from web.routes import auth, categories, subscriptions, reports, bot_info

app = FastAPI(title="Subboy API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        config.WEB_ORIGIN,
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(subscriptions.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(bot_info.router, prefix="/api")


# Раздаём статику subboy: приоритет — собранное React-приложение (subboy/dist)
subboy_path = Path(__file__).resolve().parent.parent / "subboy"
subboy_dist = subboy_path / "dist"
if (subboy_dist / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(subboy_dist), html=True), name="subboy")
elif (subboy_path / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(subboy_path), html=True), name="subboy")


@app.get("/api/health")
def health():
    return {"status": "ok"}
