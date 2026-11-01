"""Database repository for CRUD operations."""

import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import (
    AuthorizedUser, UserSetting, WatchlistItem, TradingBudgetModel,
    SignalRecord, AlertRecord, ApprovalRequest, OrderExecution, AuditLog, utcnow
)
from config.settings import settings


class Repository:
    """Async repository for database persistence."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ----------------- Authorized Users -----------------
    async def is_user_authorized(self, telegram_id: int) -> bool:
        # Check settings config allowlist first
        if settings.is_user_authorized(telegram_id):
            return True
        # Check database
        stmt = select(AuthorizedUser).where(AuthorizedUser.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def add_authorized_user(self, telegram_id: int, username: str = None, first_name: str = None, is_admin: bool = False) -> AuthorizedUser:
        stmt = select(AuthorizedUser).where(AuthorizedUser.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            user = AuthorizedUser(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                is_admin=is_admin
            )
            self.session.add(user)
        else:
            user.username = username
            user.first_name = first_name
            user.is_admin = is_admin
        await self.session.flush()
        return user

    async def is_user_admin(self, telegram_id: int) -> bool:
        # Check settings config allowlist first (Owner is always admin)
        if settings.is_user_authorized(telegram_id):
            return True
        stmt = select(AuthorizedUser).where(AuthorizedUser.telegram_id == telegram_id, AuthorizedUser.is_admin == True)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def remove_authorized_user(self, telegram_id: int) -> bool:
        stmt = delete(AuthorizedUser).where(AuthorizedUser.telegram_id == telegram_id)
        res = await self.session.execute(stmt)
        return res.rowcount > 0

    async def get_all_authorized_users(self) -> List[AuthorizedUser]:
        stmt = select(AuthorizedUser).order_by(AuthorizedUser.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ----------------- Watchlist -----------------
    async def get_watchlist(self, user_id: int) -> List[str]:
        stmt = select(WatchlistItem.symbol).where(WatchlistItem.user_id == user_id)
        result = await self.session.execute(stmt)
        symbols = [row[0] for row in result.fetchall()]
        if not symbols:
            # Fall back to default watchlist
            return settings.get_watchlist_symbols()
        return symbols

    async def add_to_watchlist(self, user_id: int, symbol: str) -> bool:
        sym = symbol.strip().upper()
        stmt = select(WatchlistItem).where(WatchlistItem.user_id == user_id, WatchlistItem.symbol == sym)
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none() is None:
            item = WatchlistItem(user_id=user_id, symbol=sym)
            self.session.add(item)
            await self.session.flush()
            return True
        return False

    async def remove_from_watchlist(self, user_id: int, symbol: str) -> bool:
        sym = symbol.strip().upper()
        stmt = delete(WatchlistItem).where(WatchlistItem.user_id == user_id, WatchlistItem.symbol == sym)
        res = await self.session.execute(stmt)
        return res.rowcount > 0

    # ----------------- Trading Budget & Limits -----------------
    async def get_or_create_budget(self, user_id: int) -> TradingBudgetModel:
        stmt = select(TradingBudgetModel).where(TradingBudgetModel.user_id == user_id)
        result = await self.session.execute(stmt)
        budget = result.scalar_one_or_none()
        if budget is None:
            budget = TradingBudgetModel(
                user_id=user_id,
                budget=settings.DEFAULT_BUDGET,
                cash_buffer_pct=settings.DEFAULT_CASH_BUFFER_PCT,
                max_position_pct=settings.DEFAULT_MAX_POSITION_PCT,
                max_order_usd=settings.DEFAULT_MAX_ORDER_USD,
                min_order_usd=settings.DEFAULT_MIN_ORDER_USD,
                max_loss_per_trade_usd=settings.DEFAULT_MAX_LOSS_PER_TRADE_USD,
                max_daily_loss_usd=settings.DEFAULT_MAX_DAILY_LOSS_USD,
                max_trades_per_day=settings.DEFAULT_MAX_TRADES_PER_DAY,
                max_orders_per_day=settings.DEFAULT_MAX_ORDERS_PER_DAY,
                min_reward_risk=settings.DEFAULT_MIN_REWARD_RISK,
                require_stop=settings.DEFAULT_REQUIRE_STOP,
                no_entries_before=settings.NO_ENTRIES_BEFORE,
                no_entries_after=settings.NO_ENTRIES_AFTER,
                flat_by=settings.FLAT_BY,
                paper=True
            )
            self.session.add(budget)
            await self.session.flush()
        return budget

    async def update_budget(self, user_id: int, **kwargs) -> TradingBudgetModel:
        budget = await self.get_or_create_budget(user_id)
        for k, v in kwargs.items():
            if hasattr(budget, k):
                setattr(budget, k, v)
        await self.session.flush()
        return budget

    # ----------------- Approval Requests -----------------
    async def create_approval_request(self, req: ApprovalRequest) -> ApprovalRequest:
        self.session.add(req)
        await self.session.flush()
        return req

    async def get_approval_request(self, approval_id: str) -> Optional[ApprovalRequest]:
        stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_approval_status(self, approval_id: str, status: str) -> Optional[ApprovalRequest]:
        req = await self.get_approval_request(approval_id)
        if req:
            req.status = status
            req.decided_at = utcnow()
            await self.session.flush()
        return req

    # ----------------- Order Executions -----------------
    async def create_order_execution(self, execution: OrderExecution) -> OrderExecution:
        self.session.add(execution)
        await self.session.flush()
        return execution

    async def get_order_execution_by_broker_id(self, broker_order_id: str) -> Optional[OrderExecution]:
        stmt = select(OrderExecution).where(OrderExecution.broker_order_id == broker_order_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_orders_today(self, symbol: Optional[str] = None) -> List[OrderExecution]:
        today_start = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(OrderExecution).where(OrderExecution.submitted_at >= today_start)
        if symbol:
            stmt = stmt.where(OrderExecution.symbol == symbol.upper())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ----------------- Alerts -----------------
    async def add_alert(self, alert: AlertRecord) -> AlertRecord:
        self.session.add(alert)
        await self.session.flush()
        return alert

    async def get_active_alerts(self, user_id: Optional[int] = None) -> List[AlertRecord]:
        stmt = select(AlertRecord).where(AlertRecord.is_active == True)
        if user_id:
            stmt = stmt.where(AlertRecord.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_alerts(self, user_id: int) -> List[AlertRecord]:
        stmt = select(AlertRecord).where(AlertRecord.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_alert(self, alert_id: int, user_id: int) -> bool:
        stmt = delete(AlertRecord).where(AlertRecord.id == alert_id, AlertRecord.user_id == user_id)
        res = await self.session.execute(stmt)
        return res.rowcount > 0

    async def set_alert_status(self, alert_id: int, user_id: int, is_active: bool) -> bool:
        stmt = update(AlertRecord).where(
            AlertRecord.id == alert_id, AlertRecord.user_id == user_id
        ).values(is_active=is_active)
        res = await self.session.execute(stmt)
        return res.rowcount > 0

    async def mark_alert_triggered(self, alert_id: int) -> None:
        stmt = select(AlertRecord).where(AlertRecord.id == alert_id)
        result = await self.session.execute(stmt)
        alert = result.scalar_one_or_none()
        if alert:
            alert.triggered_at = utcnow()
            alert.trigger_count += 1
            if not alert.rearm:
                alert.is_active = False
            await self.session.flush()

    # ----------------- User Settings -----------------
    async def get_user_setting(self, user_id: int, key: str, default: str = "") -> str:
        stmt = select(UserSetting.value).where(UserSetting.user_id == user_id, UserSetting.key == key)
        result = await self.session.execute(stmt)
        val = result.scalar_one_or_none()
        return val if val is not None else default

    async def set_user_setting(self, user_id: int, key: str, value: str) -> None:
        stmt = select(UserSetting).where(UserSetting.user_id == user_id, UserSetting.key == key)
        result = await self.session.execute(stmt)
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            self.session.add(UserSetting(user_id=user_id, key=key, value=value))
        await self.session.flush()

    # ----------------- Audit Log -----------------
    async def log_audit(self, action: str, details: str, user_id: Optional[int] = None) -> None:
        log_entry = AuditLog(user_id=user_id, action=action, details=details, timestamp=utcnow())
        self.session.add(log_entry)
        await self.session.flush()
