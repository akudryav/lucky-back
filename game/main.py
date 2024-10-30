import asyncio
import random

from app.database import *

from app.config import settings
import redis.asyncio as aredis
import json
from loguru import logger

session_redis = aredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=1)

class Croupier:
    def __init__(self, game_name):
        self.game_name = game_name

        self.is_started = False

        self.game_id = None
        self.game_hash = None
        self.game_kaf = None
        self.end_kaf = None

        self.auto_pickup = {
            '2.1': [
                {
                'bet_id': 1,
                'user_id': 1,
                'amount': 200
            }
            ]
        }

    def add_auto_pickup(self, bet_id):
        pass



async def publish_to_channel(croupier: Croupier):
    channel_name = croupier.game_name + ':game'

    while True:
        value = random.uniform(1, 25)
        end_kaf =  round(value, 2)
        end_kaf = 2

        kaf = 1.00
        croupier.is_started = True
        while True:
            rounded_kaf = round(kaf, 2)
            # await session_redis.publish(channel_name, f"0:x{rounded_kaf}")


            if rounded_kaf >= end_kaf:
                croupier.is_started = False
                # await session_redis.publish(channel_name, f"0:game_end:kaf:x{rounded_kaf}")
                await asyncio.sleep(2)

                for sleep in range(5):
                    # await session_redis.publish(channel_name, f"0:wait_new_game:{sleep}")
                    await asyncio.sleep(1)

                break
            else:
                await asyncio.sleep(0.05)
                kaf += 0.01


async def handler_clients(croupier: Croupier):
    channel_name = croupier.game_name + ':bets'

    user_channel_name = croupier.game_name + ':game'

    pubsub = session_redis.pubsub()

    await pubsub.subscribe(channel_name)

    while True:
        try:
            async with get_db() as db:
                while True:
                    message = await pubsub.get_message(ignore_subscribe_messages=True)
                    if message:
                        try:
                            json_data = json.loads(message['data'])
                            if json_data['type'] == 'bet':
                                stmt = select(User).where(User.tg_id == int(json_data['user_id']))
                                result = await db.execute(stmt)
                                current_user = result.scalars().first()

                                if croupier.is_started:
                                    print('Не можете поставить на эту игру')
                                    response = str(current_user.tg_id) + ':' + '{"type": "bet","status": false,"message": "GAME_STARTED"}'
                                    await session_redis.publish(user_channel_name, response)
                                    continue

                                if not current_user.balance >= json_data['amount']:
                                    print(current_user.balance)
                                    response = str(current_user.tg_id) + ':' + '{"type": "bet","status": false,"message": "NO_MONEY"}'
                                    await session_redis.publish(user_channel_name, response)
                                    continue

                                #Создание ставки, добавление её в список ставок и тд

                        except json.JSONDecodeError:
                            logger.info(f'invalid json: {message}')
                            continue
                    await asyncio.sleep(0.1)

        # Проверить надо
        except ConnectionError as e:
            logger.error(f'Error connect to db: {e}')
        finally:
            await pubsub.unsubscribe(channel_name)
            await pubsub.close()



async def main():
    game_name = 'hamster'
    croupier = Croupier(game_name)

    asyncio.create_task(handler_clients(croupier))

    await publish_to_channel(croupier)


if __name__ == "__main__":
    asyncio.run(main())
