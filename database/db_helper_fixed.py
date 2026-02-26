"""
Альтернативная версия db_helper с более надежным подключением
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .models import Base
from config import config
from urllib.parse import urlparse

class DatabaseHelper:
    def __init__(self, url: str, echo: bool = False):
        # Парсим URL для извлечения параметров
        parsed = urlparse(url.replace("postgresql+asyncpg://", "postgresql://"))
        
        # Создаем engine с явными параметрами подключения
        self.engine = create_async_engine(
            url=url,
            echo=echo,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=5,
            max_overflow=10,
            # Дополнительные параметры для Windows
            future=True,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    async def dispose(self):
        await self.engine.dispose()

    async def session_getter(self) -> AsyncSession:
        async with self.session_factory() as session:
            yield session

db_helper = DatabaseHelper(config.DATABASE_URL)
