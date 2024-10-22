import secrets
from fastapi import FastAPI, HTTPException, Depends
import redis.asyncio as aredis
from sqlalchemy.orm import joinedload

from app.config import settings
from app.database import get_db, User
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth_token")

# Время жизни токена в секундах (например, 30 минут)
TOKEN_EXPIRATION_SECONDS = 1800


session_redis = aredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=1)

async def generate_token():
    return secrets.token_urlsafe(64)


async def auth_user(user_id: str):
    token = await generate_token()
    await session_redis.setex(token, TOKEN_EXPIRATION_SECONDS, user_id)
    return token


async def verify_token(token: str = Depends(oauth2_scheme)):
    user_id = await session_redis.get(token)
    if user_id:
        user_id = user_id.decode("utf-8")
        async with get_db() as db:
            current_user = db.query(User).filter(User.tg_id == str(user_id)).first()
            return current_user

    raise HTTPException(status_code=401, detail="Invalid or expired token")


async def verify_token_with_bets(token: str = Depends(oauth2_scheme)):
    user_id = await session_redis.get(token)
    if user_id:
        user_id = user_id.decode("utf-8")
        async with get_db() as db:
            current_user = db.query(User).options(joinedload(User.bets)).filter(User.tg_id == str(user_id)).first()
            return current_user

    raise HTTPException(status_code=401, detail="Invalid or expired token")
