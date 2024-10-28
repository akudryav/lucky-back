import json
from cgi import print_environ_usage
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException, Depends, FastAPI
from fastapi.responses import FileResponse
from sqlalchemy.sql.functions import current_user
from fastapi_socketio import SocketManager

from bot.bot import bot
from web.auth import verify_token, auth_user, verify_token_with_bets, verify_token_with_withdrawals, verify_token_with_payments
from app.config import settings
from app.schemas import *

from aiogram.utils.web_app import check_webapp_signature, safe_parse_webapp_init_data

router = APIRouter()

@router.get("/demo")
async def demo_handler():
    return FileResponse(Path(__file__).parent.resolve() / "demo.html")

@router.post("/auth")
async def auth(request: Request):
    data = await request.form()
    if check_webapp_signature(bot.token, data["_auth"]):
        web_app_init_data = safe_parse_webapp_init_data(token=bot.token, init_data=data["_auth"])

        auth_token = await auth_user(web_app_init_data.user.id)
        return {
            "ok": True,
            "auth_token": auth_token
        }

    raise HTTPException(status_code=401, detail={"ok": False, "err": "Unauthorized"})

@router.get("/user", response_model=User)
async def get_current_user(current_user: User = Depends(verify_token)):
    return current_user

@router.get("/bet_history", response_model=UserBetHistory)
async def get_bet_history(current_user: str = Depends(verify_token_with_bets)):
    bets = current_user.bets

    user_bet_history = UserBetHistory(
        bets=[
            Bet(
                id=bet.game_id,
                gameKey=bet.game.hash,
                amount=bet.amount,
                coefficient=bet.game.crash_number,
                profit=bet.profit,
                is_win=bet.is_win
            )
            for bet in bets
        ]
    )

    return user_bet_history

@router.get("/payment_history", response_model=UserPaymentHistory)
async def get_payment_history(current_user: str = Depends(verify_token_with_payments)):
    payments = current_user.payments

    user_payment_history = UserPaymentHistory(
        payments=[
            Payment(
                id=payment.id,
                user_id=payment.user_id
            )
            for payment in payments
        ]
    )

    return user_payment_history

@router.get("/withdrawal_history", response_model=UserWithdrawalHistory)
async def get_withdrawal_history(current_user: str = Depends(verify_token_with_withdrawals)):
    withdrawals = current_user.withdrawals

    user_withdrawal_history = UserWithdrawalHistory(
        withdrawals=[
            Withdrawal(
                id=withdrawal.id,
                user_id=withdrawal.user_id
            )
            for withdrawal in withdrawals
        ]
    )

    return user_withdrawal_history
