from pydantic import BaseModel
from typing import List, Optional

from app.models import Payment


class User(BaseModel):
    tg_id: int
    balance: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class Bet(BaseModel):
    id: int
    gameKey: str
    amount: int
    coefficient: float
    profit: int
    is_win: bool

class UserBetHistory(BaseModel):
    bets: List[Bet]



class Payment(BaseModel):
    id: int
    user_id: int

class UserPaymentHistory(BaseModel):
    payments: List[Payment]



class Withdrawal(BaseModel):
    id: int
    user_id: int

class UserWithdrawalHistory(BaseModel):
    withdrawals: List[Withdrawal]