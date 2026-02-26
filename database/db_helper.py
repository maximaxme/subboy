from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from .models import Base
from config import config

class DatabaseHelper:
    def __init__(self, url: str, echo: bool = False):
        # Используем NullPool для избежания проблем с пулом соединений на Windows
        # Это создает новое соединение для каждого запроса, но более надежно
        self.engine = create_async_engine(
            url=url,
            echo=echo,
            poolclass=NullPool,  # Не используем пул - создаем новое соединение каждый раз
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    async def dispose(self):
        await self.engine.dispose()

    async def session_getter(self) -> AsyncSession:
        async with self.session_factory() as session:
            yield session

db_helper = DatabaseHelper(config.DATABASE_URL)
