from logging import DEBUG

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from web.bot_handlers import bot_router
from web.web_app import router
from contextlib import asynccontextmanager
import redis.asyncio as aredis
import bot.handlers

from loguru import logger

DEBUG=False

@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("🚀 Starting worker")
    if not DEBUG:
        from bot.configuration import config_bot
        await config_bot()
    yield
    logger.info("⛔ Stopping worker")

app = FastAPI(lifespan=lifespan)

init_redis = aredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
# session_redis = aredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=1)
# cache_redis = aredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=2)

origins = ['*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


Base.metadata.create_all(bind=engine)

app.include_router(bot_router)

app.include_router(router)
