
from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)

from aiogram.utils.markdown import hbold
from aiogram.types import Message
from bot.bot import telegram_router, bot
from app.database import *
from app.config import settings
import base64
from io import BytesIO

import redis.asyncio as aredis

cache_redis = aredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=2)


@telegram_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    async with get_db() as db:
        # Регистрация пользователя
        stmt = select(User).where(User.tg_id == message.from_user.id)
        result = await db.execute(stmt)
        user = result.scalars().first()

        # user_photos = await bot.get_user_profile_photos(user_id=message.from_user.id)
        #
        # if user_photos.total_count > 0:
        #     # Получаем аватарку
        #     latest_photo = user_photos.photos[-1][-1]  # Get the highest resolution photo
        #     file_info = await bot.get_file(latest_photo.file_id)
        #     file = await bot.download_file(file_info.file_path)
        #
        #     # Корнвертируем в base64
        #     photo_bytes = BytesIO(file.read())
        #     photo_base64 = base64.b64encode(photo_bytes.getvalue()).decode('utf-8')
        #
        #     # Проверяем аватарку на изменения
        #     redis_key = f"user_avatar:{message.from_user.id}"
        #     cached_photo_base64 = await cache_redis.get(redis_key)
        #
        #     if cached_photo_base64 != photo_base64:
        #         # Сохраняем
        #         await cache_redis.set(redis_key, photo_base64)

        if not user:
            new_user = User(
                tg_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )
            db.add(new_user)
            await db.commit()

        else:
            change = False
            if user.first_name != message.from_user.first_name:
                user.first_name = message.from_user.first_name
                change = True

            if user.last_name != message.from_user.last_name:
                user.last_name = message.from_user.last_name
                change = True

            if user.username != message.from_user.username:
                user.username = message.from_user.username
                change = True

            if change:
                await db.commit()

        await bot.set_chat_menu_button(
            chat_id=message.chat.id,
            menu_button=MenuButtonWebApp(text="Play Game", web_app=WebAppInfo(url=f"{settings.WEBAPP_HOST_URL}{settings.WEBAPP_ROUTE}")),
        )
        await message.answer(f"Добро пожаловать в игру, {message.from_user.full_name}!")
