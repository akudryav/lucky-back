import asyncio
import random
import hashlib

from app.database import *
from game.Croupier import Croupier
from sqlalchemy.orm import joinedload
from app.config import settings
import redis.asyncio as aredis
import json
from loguru import logger

session_redis = aredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=1)

SLEEP_TIME_BETWEEN_GAME=5

#
# import math
# import random
#
# def crash_probability(multiplier, t, base_chance):
#     m = math.log(multiplier + 1)
#     return base_chance + (1 - math.exp(-m * t))
#
# def get_crash_multiplier(casino_profit):
#     k = 0.03
#     t = 0
#     multiplier = 1
#     crashed = False
#     base_chance = 0.00002
#
#     # Adjust the maximum multiplier based on the casino's profit
#     if casino_profit > 10000:
#         max_multiplier = 100  # High profit, high multipliers
#     elif casino_profit > 0:
#         max_multiplier = 10   # Moderate profit, moderate multipliers
#     else:
#         max_multiplier = 2    # Low or negative profit, low multipliers
#
#     while not crashed:
#         k += 0.33
#         multiplier = min(math.exp(k * t), max_multiplier)
#         base_chance += 0.0012
#         prob_of_crash = crash_probability(multiplier, t, base_chance)
#
#         if random.random() < prob_of_crash:
#             crashed = True
#             return multiplier
#         else:
#             t += 0.01
#
# # Example usage
# casino_profit = 11000  # Example profit value
# for _ in range(1000):
#     crash_multiplier = get_crash_multiplier(casino_profit)
#     print(crash_multiplier)


async def publish_to_channel(croupier: Croupier):
    channel_name = croupier.game_name + ':game'

    while True:
        new_game = await croupier.create_new_game()

        croupier.game_id = new_game.id
        croupier.game_kaf = new_game.crash_number

        response = f'0:{{"type": "game", "game_id": "{croupier.game_id}"}}'
        await session_redis.publish(channel_name, response)

        end_kaf = new_game.crash_number

        croupier.kaf_now = 1.00
        for sleep in range(SLEEP_TIME_BETWEEN_GAME, 0, -1):
            await session_redis.publish(channel_name, f'0:{{"type": "wait_game", "wait": "{sleep}"}}')
            await asyncio.sleep(1)

        croupier.is_started = True
        croupier.game_crashed = False
        while True:
            croupier.kaf_now = round(croupier.kaf_now, 2)
            await session_redis.publish(channel_name, f'0:{{"type": "play_game", "c": "{croupier.kaf_now:.2f}" }}')

            if croupier.kaf_now >= end_kaf:
                croupier.is_started = False
                croupier.game_crashed = True

                # Краш. Делаем луз всем
                async with get_db() as db:
                    stmt = select(PlayerBet).options(
                        joinedload(PlayerBet.user)
                    ).where(PlayerBet.game_id == int(croupier.game_id), PlayerBet.is_win == None)
                    result = await db.execute(stmt)

                    bets = result.scalars().all()

                    for bet in bets:
                        bet.profit = 0
                        bet.is_win = False
                        bet.coff = 0

                        # Личный алерт юзеру

                        # Глобальное уведомление краше


                    await db.commit()

                await session_redis.publish(channel_name, f'0:{{"type": "game_end", "game_id": "{croupier.game_id}", "end_c": "{end_kaf}" }}')
                break
            else:
                # Статичное время между увеличением
                await asyncio.sleep(0.05)

                # Рандомное время сна между увеличением кэфа ( Прикольная штука, лудикам понравится :) )
                # await asyncio.sleep(random.uniform(0.01, 0.30))

                croupier.kaf_now += 0.01



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
                                user_id = int(json_data['user_id'])
                                amount = json_data['amount']
                                button_id = json_data['button_id']
                                auto_pickup = json_data['auto_pickup']


                                stmt = select(User).where(User.tg_id == user_id)
                                result = await db.execute(stmt)
                                current_user = result.scalars().first()


                                if croupier.is_started:
                                    # игра запущенная, ставки не будет
                                    response = f'{current_user.tg_id}:{{"type": "bet","status": false,"message": "GAME_STARTED"}}'
                                    await session_redis.publish(user_channel_name, response)
                                    continue

                                if not current_user.balance >= float(json_data['amount']):
                                    # всё хорошо, но клиент бомжик
                                    response = f'{current_user.tg_id}:{{"type": "bet","status": false,"message": "NO_MONEY"}}'
                                    await session_redis.publish(user_channel_name, response)
                                    continue

                                # Проверка на существование дубл ставки
                                stmt = select(PlayerBet).where(PlayerBet.user_id == user_id,
                                                               PlayerBet.game_id == croupier.game_id, PlayerBet.button_id == button_id)
                                result = await db.execute(stmt)
                                has_bet = result.scalars().first()

                                if has_bet:
                                    response = f'{current_user.tg_id}:{{"type": "bet","status": false,"message": "DUBLICATED_BET"}}'
                                    await session_redis.publish(user_channel_name, response)
                                    continue

                                #Создание ставки, добавление её в список ставок и отправка всем юзерам
                                new_bet = PlayerBet(
                                    user_id=current_user.tg_id,
                                    game_id=croupier.game_id,
                                    button_id=button_id,
                                    amount=amount,
                                )
                                db.add(new_bet)
                                current_user.balance -= amount

                                await db.commit()
                                await db.refresh(new_bet)
                                await db.refresh(current_user)

                                # возврат ставки типу
                                response = (f'{current_user.tg_id}:{{"type": "bet","status": true, "bet_id": "{new_bet.id}", "amount": "{new_bet.amount}", '
                                            f'"button_id": "{new_bet.button_id}", "auto_pickup": "{auto_pickup}", "new_balance": "{current_user.balance}" }}')
                                await session_redis.publish(user_channel_name, response)


                                # Глобальный возврат ставки
                                full_username = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip()
                                response = f'0:{{"type": "player_bet", "user_id": "{current_user.tg_id}" ,"user": "{full_username}", "amount": {amount} }}'
                                await session_redis.publish(user_channel_name, response)
                                continue

                            if json_data['type'] == 'new_connect':
                                user_id = int(json_data['user_id'])

                                # Вернем юзеру текущую игру, текущие ставки, и в общий изменение онлайна
                                stmt = select(Game).options(
                                    joinedload(Game.bets).joinedload(PlayerBet.user)
                                ).where(Game.id == int(croupier.game_id))
                                result = await db.execute(stmt)

                                current_game = result.scalars().first()
                                for bet in current_game.bets:

                                    full_username = f"{bet.user.first_name or ''} {bet.user.last_name or ''}".strip()

                                    response = f'{user_id}:{{"type": "player_bet", "user_id": "{bet.user_id}", "user": "{full_username}", "amount": {bet.amount} }}'
                                    await session_redis.publish(user_channel_name, response)

                                #Возврат активных ставок юзера
                                stmt = select(Game).options(
                                    joinedload(Game.bets).joinedload(PlayerBet.user)
                                ).where(Game.id == int(croupier.game_id), PlayerBet.user_id == user_id, PlayerBet.is_win == None)
                                result = await db.execute(stmt)

                                user_bets = result.scalars().first()
                                if user_bets:
                                    for user_bet in user_bets.bets:

                                        response = (f'{current_user.tg_id}:{{"type": "bet","status": true, "bet_id": "{user_bet.id}", "amount": "{user_bet.amount}", '
                                                    f'"button_id": "{user_bet.button_id}", "auto_pickup": "0", "new_balance": "{user_bet.user.balance}" }}')
                                        await session_redis.publish(user_channel_name, response)

                                # возврат текущей игры
                                response = f'{user_id}:{{"type": "game", "game_id": "{croupier.game_id}"}}'
                                await session_redis.publish(user_channel_name, response)

                                # глобальное обновление онлайна
                                info = await session_redis.info(section='clients')
                                connection_count = info.get('connected_clients', 0)

                                response = f'0:{{"type": "online", "count": "{connection_count - settings.ONLINE_FIX}" }}'
                                await session_redis.publish(user_channel_name, response)

                                continue

                            if json_data['type'] == 'disconnect':
                                # обновление онлайна при дисконнекте
                                info = await session_redis.info(section='clients')
                                connection_count = info.get('connected_clients', 0)

                                response = f'0:{{"type": "online", "count": {connection_count - settings.ONLINE_FIX - 1} }}'
                                await session_redis.publish(user_channel_name, response)

                                continue

                            if json_data['type'] == 'pickup':

                                user_id = int(json_data['user_id'])
                                button_id = int(json_data['button_id'])
                                game_id = croupier.game_id

                                if croupier.is_started:

                                    stmt = select(PlayerBet).options(
                                        joinedload(PlayerBet.game),
                                        joinedload(PlayerBet.user)
                                    ).where(
                                        PlayerBet.user_id == user_id,
                                        PlayerBet.game_id == game_id,
                                        PlayerBet.button_id == button_id
                                    )
                                    result = await db.execute(stmt)

                                    user_bet = result.scalars().first()
                                    if user_bet:
                                        if user_bet.is_win is not None:
                                            response = f'{user_id}:{{"type": "pickup", "status": false, "button_id": "{button_id}", "message": "IS_BET_ENDED"}}'
                                            await session_redis.publish(user_channel_name, response)
                                            continue

                                        if croupier.game_crashed:
                                            response = f'{user_id}:{{"type": "pickup", "status": false, "button_id": "{button_id}", "message": "IS_GAME_CRASHED"}}'
                                            await session_redis.publish(user_channel_name, response)
                                            continue
                                        else:
                                            current_cof = croupier.kaf_now

                                            profit = user_bet.amount * current_cof
                                            profit = round(profit, 2)

                                            # Ставим победу, профит, кэф, прибавляем баланс
                                            user_bet.is_win = True
                                            user_bet.profit = profit
                                            user_bet.coff = current_cof
                                            user_bet.user.balance += profit

                                            await db.commit()
                                            await db.refresh(user_bet)

                                            response = f'{user_id}:{{"type": "pickup", "status": true, "profit": "{profit}", "bet_id": "{user_bet.id}", "button_id": "{user_bet.button_id}", "cof": "{current_cof}"}}'
                                            await session_redis.publish(user_channel_name, response)
                                            continue

                                    else:
                                        response = f'{user_id}:{{"type": "pickup", "status": false, "button_id": "{button_id}", "message": "BET_NOT_FOUND"}}'
                                        await session_redis.publish(user_channel_name, response)
                                        continue
                                else:
                                    response = f'{user_id}:{{"type": "pickup", "status": false, "button_id": "{button_id}", "message": "GAME_NOT_STARTED"}}'
                                    await session_redis.publish(user_channel_name, response)
                                    continue


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
