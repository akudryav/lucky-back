from os import getppid
from bot.bot import bot


from app.config import settings

from aiogram.types import MenuButtonWebApp, WebAppInfo
from loguru import logger

from app.app import init_redis

async def first_run() -> bool:
    """Check if this is the first run of service. ppid is the parent process id.
    Save ppid to redis and check it on next run. If ppid is the same - this is not the first run."""
    ppid = getppid()
    save_pid = await init_redis.get('tg_bot_ppid')
    if save_pid and int(save_pid) == ppid:
        await init_redis.close()
        return False
    await init_redis.set('tg_bot_ppid', ppid)
    await init_redis.close()
    return True


async def config_bot():
    fr = await first_run()
    if fr:
        logger.info("🚀 Configuration....")
        await bot.set_webhook(
            f"{settings.BOT_HOST_URL}{settings.BOT_ROUTE}",
            secret_token=settings.TELEGRAM_SECURITY_TOKEN,
            max_connections=100
                )

        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Play Game", web_app=WebAppInfo(url=f"{settings.WEBAPP_HOST_URL}{settings.WEBAPP_ROUTE}"))
        )

