import asyncio
from app.database import get_db
from app.config import settings
import redis.asyncio as aredis

# Initialize the Redis client
session_redis = aredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=1)


async def publish_to_channel(channel_name):
    kaf = 0.0
    while True:
        rounded_kaf = round(kaf, 2)
        await session_redis.publish(channel_name, f"x{rounded_kaf}")
        kaf += 0.1
        # await asyncio.sleep(0.7)



async def main():
    channel_name = 'game'

    await publish_to_channel(channel_name)


if __name__ == "__main__":
    asyncio.run(main())
