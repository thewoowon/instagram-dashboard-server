from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL

if DATABASE_URL.startswith("postgresql://"):
    async_database_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    sync_database_url = DATABASE_URL
elif DATABASE_URL.startswith("postgresql+asyncpg://"):
    async_database_url = DATABASE_URL
    sync_database_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
else:
    async_database_url = DATABASE_URL
    sync_database_url = DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")

# transaction pooler는 prepared statement 미지원
# asyncpg는 URL 쿼리 파라미터로 statement_cache_size=0 전달
if "statement_cache_size" not in async_database_url:
    sep = "&" if "?" in async_database_url else "?"
    async_database_url = f"{async_database_url}{sep}prepared_statement_cache_size=0"

async_engine = create_async_engine(async_database_url, echo=settings.DEBUG)

AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Alembic 전용 sync 엔진
sync_engine = create_engine(sync_database_url, echo=False, pool_pre_ping=True)

SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)
