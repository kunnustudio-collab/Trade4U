"""Unit tests for the mandatory Order Approval Workflow."""

import os
import unittest
import datetime
import tempfile
import uuid
import json
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database.models import Base, ApprovalRequest, utcnow
from database.repository import Repository
from services.approval_service import ApprovalService, ApprovalValidationError
from services.broker_service import MockPaperBroker


class TestBotApprovalWorkflow(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_url = f"sqlite+aiosqlite:///{self.temp_db.name}"

        self.engine = create_async_engine(self.db_url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_session():
            async with self.session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        # Patch database session in approval_service
        self.session_patch = patch("services.approval_service.get_session", mock_get_session)
        self.session_patch.start()

        # Patch broker with MockPaperBroker
        self.mock_broker = MockPaperBroker(initial_balance=5000.0)
        self.broker_patch = patch("services.approval_service.get_broker_instance", return_value=self.mock_broker)
        self.broker_patch.start()

        # Add authorized user
        async with self.session_factory() as session:
            repo = Repository(session)
            await repo.add_authorized_user(1001, "trader", "Trader", is_admin=True)
            await session.commit()

        from utils.ny_time import NY_TZ
        self.market_now = datetime.datetime(2026, 10, 19, 10, 15, tzinfo=NY_TZ)
        self.service = ApprovalService()

    async def asyncTearDown(self):
        self.broker_patch.stop()
        self.session_patch.stop()
        await self.engine.dispose()
        try:
            os.remove(self.temp_db.name)
        except OSError:
            pass

    async def test_order_preview_generation_and_approval(self):
        valid_order = {
            "symbol": "TSLA",
            "side": "buy",
            "qty": "8",
            "type": "market",
            "time_in_force": "day",
            "order_class": "bracket",
            "take_profit_limit_price": "370.04",
            "stop_loss_stop_price": "358.32",
            "plan": {"entry": 364.18, "stop": 358.32, "target": 370.04}
        }

        # Step 1-3: Generate approval preview
        passed, req, msg = await self.service.create_approval_request(1001, valid_order, buying_power=5000.0, now=self.market_now)
        self.assertTrue(passed)
        self.assertIsNotNone(req)
        self.assertEqual(req.status, "PENDING")
        self.assertEqual(req.symbol, "TSLA")

        # Step 4-8: Approve order manually
        res = await self.service.process_approval(req.id, 1001, now=self.market_now)
        self.assertIsNotNone(res["broker_order_id"])
        self.assertEqual(res["symbol"], "TSLA")
        self.assertEqual(res["status"], "FILLED")
        self.assertEqual(res["qty"], 8)

        # Step 8 check: Request in DB is now APPROVED
        async with self.session_factory() as session:
            repo = Repository(session)
            db_req = await repo.get_approval_request(req.id)
            self.assertEqual(db_req.status, "APPROVED")

    async def test_duplicate_approval_prevention(self):
        valid_order = {
            "symbol": "TSLA",
            "side": "buy",
            "qty": "8",
            "type": "market",
            "time_in_force": "day",
            "order_class": "bracket",
            "take_profit_limit_price": "370.04",
            "stop_loss_stop_price": "358.32",
            "plan": {"entry": 364.18, "stop": 358.32, "target": 370.04}
        }
        passed, req, _ = await self.service.create_approval_request(1001, valid_order, now=self.market_now)
        # First approval succeeds
        await self.service.process_approval(req.id, 1001, now=self.market_now)

        # Second approval must fail due to idempotency protections
        with self.assertRaises(ApprovalValidationError) as ctx:
            await self.service.process_approval(req.id, 1001, now=self.market_now)
        self.assertIn("already 'APPROVED'", str(ctx.exception))

    async def test_unauthorized_user_approval_is_blocked(self):
        valid_order = {
            "symbol": "TSLA",
            "side": "buy",
            "qty": "8",
            "type": "market",
            "time_in_force": "day",
            "order_class": "bracket",
            "take_profit_limit_price": "370.04",
            "stop_loss_stop_price": "358.32",
            "plan": {"entry": 364.18, "stop": 358.32, "target": 370.04}
        }
        passed, req, _ = await self.service.create_approval_request(1001, valid_order, now=self.market_now)

        # Unauthorized user 9999 attempts approval
        with self.assertRaises(ApprovalValidationError) as ctx:
            await self.service.process_approval(req.id, 9999, now=self.market_now)
        self.assertIn("Unauthorized", str(ctx.exception))

    async def test_expired_approval_is_rejected(self):
        valid_order = {
            "symbol": "TSLA",
            "side": "buy",
            "qty": "8",
            "type": "market",
            "time_in_force": "day",
            "order_class": "bracket",
            "take_profit_limit_price": "370.04",
            "stop_loss_stop_price": "358.32",
            "plan": {"entry": 364.18, "stop": 358.32, "target": 370.04}
        }
        # TTL of -10 seconds (already expired)
        passed, req, _ = await self.service.create_approval_request(1001, valid_order, ttl_seconds=-10, now=self.market_now)

        with self.assertRaises(ApprovalValidationError) as ctx:
            await self.service.process_approval(req.id, 1001, now=self.market_now)
        self.assertIn("expired", str(ctx.exception))

    async def test_order_rejection(self):
        valid_order = {
            "symbol": "TSLA",
            "side": "buy",
            "qty": "8",
            "type": "market",
            "time_in_force": "day",
            "order_class": "bracket",
            "take_profit_limit_price": "370.04",
            "stop_loss_stop_price": "358.32",
            "plan": {"entry": 364.18, "stop": 358.32, "target": 370.04}
        }
        passed, req, _ = await self.service.create_approval_request(1001, valid_order, now=self.market_now)
        rejected = await self.service.reject_approval(req.id, 1001)
        self.assertTrue(rejected)

        # Cannot approve rejected order
        with self.assertRaises(ApprovalValidationError):
            await self.service.process_approval(req.id, 1001, now=self.market_now)


if __name__ == "__main__":
    unittest.main()
