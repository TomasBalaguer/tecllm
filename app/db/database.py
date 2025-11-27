from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()

# Convert postgresql:// to postgresql+asyncpg:// for async
async_database_url = settings.database_url.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# Async engine for the application
async_engine = create_async_engine(
    async_database_url,
    echo=False,
    future=True,
)

# Async session factory
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync engine for migrations and initial setup
sync_engine = create_engine(
    settings.database_url,
    echo=False,
)


async def init_db():
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncSession:
    """Dependency to get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_session() -> Session:
    """Get sync session for scripts."""
    with Session(sync_engine) as session:
        yield session
