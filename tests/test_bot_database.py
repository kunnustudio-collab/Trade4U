"""Unit tests for database models and repository persistence."""

import unittest
import asyncio
import os
import tempfile
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database.models import Base, ApprovalRequest, AlertRecord, OrderExecution, utcnow
from database.repository import Repository


class TestBotDatabase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_url = f"sqlite+aiosqlite:///{self.temp_db.name}"

        self.engine = create_async_engine(self.db_url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()
        try:
            os.remove(self.temp_db.name)
        except OSError:
            pass

    async def test_authorized_user_crud(self):
        async with self.session_factory() as session:
            repo = Repository(session)
            self.assertFalse(await repo.is_user_authorized(12345))

            await repo.add_authorized_user(12345, "johndoe", "John", is_admin=True)
            await session.commit()

        async with self.session_factory() as session:
            repo = Repository(session)
            self.assertTrue(await repo.is_user_authorized(12345))

    async def test_watchlist_crud(self):
        async with self.session_factory() as session:
            repo = Repository(session)
            await repo.add_to_watchlist(1001, "TSLA")
            await repo.add_to_watchlist(1001, "NVDA")
            await session.commit()

        async with self.session_factory() as session:
            repo = Repository(session)
            syms = await repo.get_watchlist(1001)
            self.assertIn("TSLA", syms)
            self.assertIn("NVDA", syms)

            await repo.remove_from_watchlist(1001, "TSLA")
            await session.commit()

        async with self.session_factory() as session:
            repo = Repository(session)
            syms = await repo.get_watchlist(1001)
            self.assertNotIn("TSLA", syms)
            self.assertIn("NVDA", syms)

    async def test_budget_persistence(self):
        async with self.session_factory() as session:
            repo = Repository(session)
            b = await repo.get_or_create_budget(1001)
            self.assertEqual(b.budget, 5000.0)

            await repo.update_budget(1001, budget=10000.0, max_loss_per_trade_usd=100.0)
            await session.commit()

        async with self.session_factory() as session:
            repo = Repository(session)
            b = await repo.get_or_create_budget(1001)
            self.assertEqual(b.budget, 10000.0)
            self.assertEqual(b.max_loss_per_trade_usd, 100.0)

    async def test_approval_and_execution_persistence(self):
        req_id = str(uuid.uuid4())
        async with self.session_factory() as session:
            repo = Repository(session)
            req = ApprovalRequest(
                id=req_id,
                fingerprint="fingerprint123",
                user_id=1001,
                symbol="TSLA",
                side="buy",
                qty=8,
                order_type="market",
                stop_loss=358.32,
                take_profit=370.04,
                estimated_notional=2913.44,
                max_planned_risk=46.88,
                status="PENDING",
                created_at=utcnow(),
                expires_at=utcnow(),
                order_payload_json='{"symbol": "TSLA"}'
            )
            await repo.create_approval_request(req)
            await session.commit()

        async with self.session_factory() as session:
            repo = Repository(session)
            fetched = await repo.get_approval_request(req_id)
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched.symbol, "TSLA")
            self.assertEqual(fetched.status, "PENDING")

            await repo.update_approval_status(req_id, "APPROVED")
            await session.commit()

        async with self.session_factory() as session:
            repo = Repository(session)
            fetched = await repo.get_approval_request(req_id)
            self.assertEqual(fetched.status, "APPROVED")

    async def test_alerts_lifecycle(self):
        async with self.session_factory() as session:
            repo = Repository(session)
            alert = AlertRecord(
                user_id=1001,
                symbol="TSLA",
                rule_type="target",
                price=370.04,
                is_active=True,
                rearm=False
            )
            created = await repo.add_alert(alert)
            aid = created.id
            await session.commit()

        async with self.session_factory() as session:
            repo = Repository(session)
            active = await repo.get_active_alerts(1001)
            self.assertEqual(len(active), 1)

            # Mark triggered
            await repo.mark_alert_triggered(aid)
            await session.commit()

        async with self.session_factory() as session:
            repo = Repository(session)
            active = await repo.get_active_alerts(1001)
            self.assertEqual(len(active), 0)  # Deactivated after trigger since rearm=False


if __name__ == "__main__":
    unittest.main()
