import time
from aiogram import Bot, Dispatcher
from app.config import settings
from loguru import logger
from aiogram import Bot, Dispatcher, Router, types

telegram_router = Router(name="telegram")

dp = Dispatcher()
dp.include_router(telegram_router)

bot = Bot(token=settings.BOT_TOKEN)

