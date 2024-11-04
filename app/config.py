from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    DATABASE_URL: str
    BOT_TOKEN: str
    TELEGRAM_SECURITY_TOKEN: str

    BOT_HOST_URL: str
    BOT_ROUTE: str

    WEBAPP_HOST_URL: str
    WEBAPP_ROUTE: str

    REDIS_HOST: str
    REDIS_PORT: str

    SERVER_SALT: str

    ONLINE_FIX: int

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), '../.env')


settings = Settings()