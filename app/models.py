from email.policy import default

from sqlalchemy import Column, BigInteger, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class User(Base):
    __tablename__ = 'user'

    tg_id = Column(BigInteger, primary_key=True, unique=True)
    balance = Column(Integer, default=0)
    username = Column(String, default=None)
    first_name = Column(String, default=None)
    last_name = Column(String, default=None)

    bets = relationship('PlayerBet', back_populates='user')
    payments = relationship('Payment', back_populates='user')


class Game(Base):
    __tablename__ = 'game'

    id = Column(Integer, primary_key=True, autoincrement=True)
    profit = Column(BigInteger, default=None)
    server_salt = Column(String)
    crash_number = Column(Float)
    hash = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    ended_at = Column(DateTime, onupdate=datetime.now)

    bets = relationship('PlayerBet', back_populates='game')


class PlayerBet(Base):
    __tablename__ = 'player_bets'

    user_id = Column(BigInteger, ForeignKey('user.tg_id'), primary_key=True)
    game_id = Column(Integer, ForeignKey('game.id'), primary_key=True)
    amount = Column(Integer)
    profit = Column(Integer)
    is_win = Column(Boolean)

    user = relationship('User', back_populates='bets')
    game = relationship('Game', back_populates='bets')


class Payment(Base):
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('user.tg_id'))

    user = relationship('User', back_populates='payments')


class CrashSettings(Base):
    __tablename__ = 'crash_settings'
    key = Column(String, primary_key=True)
    value = Column(String)