"""SQLAlchemy database models for Day Trader Telegram Bot."""

import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Boolean,
    DateTime, Text, ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class AuthorizedUser(Base):
    __tablename__ = "authorized_users"

    telegram_id = Column(BigInteger, primary_key=True)
    username = Column(String(64), nullable=True)
    first_name = Column(String(128), nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)


class UserSetting(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, index=True)
    key = Column(String(64), index=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class WatchlistItem(Base):
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, index=True)
    symbol = Column(String(16), index=True)
    added_at = Column(DateTime, default=utcnow)


class TradingBudgetModel(Base):
    __tablename__ = "trading_budget"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, index=True)
    budget = Column(Float, default=5000.0)
    cash_buffer_pct = Column(Float, default=10.0)
    max_position_pct = Column(Float, default=75.0)
    max_order_usd = Column(Float, default=4000.0)
    min_order_usd = Column(Float, default=5.0)
    max_loss_per_trade_usd = Column(Float, default=50.0)
    max_daily_loss_usd = Column(Float, default=150.0)
    max_trades_per_day = Column(Integer, default=3)
    max_orders_per_day = Column(Integer, default=10)
    min_reward_risk = Column(Float, default=1.0)
    require_stop = Column(Boolean, default=True)
    no_entries_before = Column(String(8), default="09:45")
    no_entries_after = Column(String(8), default="15:30")
    flat_by = Column(String(8), default="15:55")
    paper = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class SignalRecord(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), index=True)
    setup = Column(String(32))
    direction = Column(String(8), default="buy")
    price = Column(Float)
    entry_level = Column(Float)
    stop_loss = Column(Float)
    target = Column(Float)
    reward_risk = Column(Float)
    status = Column(String(32))
    data_source = Column(String(64))
    signal_time = Column(DateTime, default=utcnow)
    raw_json = Column(Text, nullable=True)


class AlertRecord(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, index=True)
    symbol = Column(String(16), nullable=True, index=True)
    rule_type = Column(String(32))  # above, below, stop, target, pct_move, time, opening_bell
    price = Column(Float, nullable=True)
    pct = Column(Float, nullable=True)
    time_at = Column(String(8), nullable=True)
    label = Column(String(128), nullable=True)
    is_active = Column(Boolean, default=True)
    rearm = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    triggered_at = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, default=0)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String(36), primary_key=True)  # UUID
    fingerprint = Column(String(64), index=True)  # SHA256 of order payload
    user_id = Column(BigInteger, index=True)
    symbol = Column(String(16), index=True)
    side = Column(String(8))  # buy, sell
    qty = Column(Integer)
    order_type = Column(String(16))  # limit, market
    limit_price = Column(Float, nullable=True)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    estimated_notional = Column(Float)
    max_planned_risk = Column(Float)
    available_buying_power = Column(Float, default=0.0)
    risk_verdict = Column(String(16), default="PASS")  # PASS or BLOCK
    status = Column(String(16), default="PENDING", index=True)  # PENDING, APPROVED, REJECTED, EXPIRED
    created_at = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime)
    decided_at = Column(DateTime, nullable=True)
    order_payload_json = Column(Text)

    executions = relationship("OrderExecution", back_populates="approval")


class OrderExecution(Base):
    __tablename__ = "order_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    approval_id = Column(String(36), ForeignKey("approval_requests.id"))
    broker_order_id = Column(String(64), nullable=True, index=True)
    client_order_id = Column(String(64), index=True)
    symbol = Column(String(16))
    side = Column(String(8))
    qty = Column(Integer)
    order_type = Column(String(16))
    status = Column(String(32), default="SUBMITTED")  # SUBMITTED, FILLED, CANCELED, REJECTED
    submitted_at = Column(DateTime, default=utcnow)
    filled_at = Column(DateTime, nullable=True)
    filled_qty = Column(Integer, default=0)
    filled_avg_price = Column(Float, nullable=True)
    broker_response_json = Column(Text, nullable=True)

    approval = relationship("ApprovalRequest", back_populates="executions")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=True)
    action = Column(String(64))
    details = Column(Text)
    timestamp = Column(DateTime, default=utcnow)
