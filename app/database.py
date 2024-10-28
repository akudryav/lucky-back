from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, registry
from app.config import settings
from contextlib import asynccontextmanager
from sqlalchemy.future import select

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False
)

mapper_registry = registry()
Base = mapper_registry.generate_base()

from app.models import *

@asynccontextmanager
async def get_db():
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
