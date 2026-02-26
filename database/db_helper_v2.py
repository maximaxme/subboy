"""
Версия db_helper с прямым подключением через asyncpg
"""
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from .models import Base
from config import config
from urllib.parse import urlparse

class DatabaseHelper:
    def __init__(self, url: str, echo: bool = False):
        # Парсим URL для получения параметров
        parsed = urlparse(url.replace("postgresql+asyncpg://", "postgresql://"))
        
        # Извлекаем параметры подключения
        self.db_params = {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 5432,
            'user': parsed.username or 'postgres',
            'password': parsed.password or '',
            'database': parsed.path.lstrip('/') or 'sub_tracker'
        }
        
        # Создаем engine с NullPool для избежания проблем с пулом
        # и используем прямое подключение через asyncpg
        self.engine = create_async_engine(
            url=url,
            echo=echo,
            poolclass=NullPool,  # Не используем пул соединений
            pool_pre_ping=False,
        )
        
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    async def dispose(self):
        await self.engine.dispose()
        
    async def get_connection(self):
        """Получить прямое подключение через asyncpg"""
        return await asyncpg.connect(**self.db_params)

    async def session_getter(self) -> AsyncSession:
        async with self.session_factory() as session:
            yield session

db_helper = DatabaseHelper(config.DATABASE_URL)
