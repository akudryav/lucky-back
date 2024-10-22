from typing import Annotated

from fastapi import APIRouter, Header
from loguru import logger
from aiogram import types

from bot.bot import bot, dp
from app.config import settings

bot_router = APIRouter(
    prefix="",
    tags=["root"],
    responses={404: {"description": "Not found"}},
)


@bot_router.get("/")
async def root() -> dict:
    return {"message": "Hello World"}


@bot_router.post(settings.BOT_ROUTE)
async def bot_webhook(update: dict,
                      x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None) -> None | dict:

    """ Register webhook endpoint for telegram bot"""
    if x_telegram_bot_api_secret_token != settings.TELEGRAM_SECURITY_TOKEN:
        logger.error("Wrong secret token !")
        return {"status": "error", "message": "Wrong secret token !"}
    telegram_update = types.Update(**update)
    await dp.feed_webhook_update(bot=bot, update=telegram_update)
