"""Mandatory Order Approval Workflow Service.

Enforces strict manual review, risk checks, expiration, idempotency,
and paper-trading-only execution.
"""

import json
import uuid
import datetime
import logging
from typing import Dict, Any, Optional, Tuple

from config.settings import settings
from database.database import get_session
from database.models import ApprovalRequest, OrderExecution, utcnow
from database.repository import Repository
from core.risk_adapter import RiskAdapter
from core.broker_ticket_adapter import BrokerTicketAdapter
from services.broker_service import get_broker_instance, BrokerError
from utils.ny_time import get_ny_now

logger = logging.getLogger(__name__)


class ApprovalValidationError(Exception):
    """Exception raised when an approval fails validation checks."""
    pass


class ApprovalService:
    """Manages the lifecycle of manual order approvals."""

    def __init__(self):
        self.risk_adapter = RiskAdapter()
        self.ticket_adapter = BrokerTicketAdapter()

    async def create_approval_request(
        self,
        user_id: int,
        order: Dict[str, Any],
        buying_power: float = 0.0,
        ttl_seconds: Optional[int] = None,
        now: Optional[datetime.datetime] = None
    ) -> Tuple[bool, Optional[ApprovalRequest], str]:
        """Step 1 & 2 & 3: Run risk check, create pending approval request in database.

        Returns (is_passed, approval_request, explanation).
        """
        ttl = ttl_seconds or settings.ORDER_APPROVAL_TIMEOUT_SECONDS
        expires_at = utcnow() + datetime.timedelta(seconds=ttl)
        fingerprint = self.ticket_adapter.calculate_fingerprint(order)

        # 1. Run Pre-trade Risk Check using original check.py logic
        risk_result = self.risk_adapter.check_orders([order], now=now)
        res0 = risk_result["results"][0]
        verdict = res0["verdict"]

        if verdict != "PASS":
            reasons_str = " | ".join(res0["reasons"])
            logger.warning("Order blocked by risk engine: %s", reasons_str)
            return False, None, f"RISK CHECK FAILED: {reasons_str}"

        # 2. Extract values for approval preview
        symbol = order["symbol"].upper()
        side = order["side"].lower()
        qty = int(order["qty"])
        order_type = order.get("type", "market")
        limit_price = float(order["limit_price"]) if order.get("limit_price") else None
        stop_loss = float(order.get("stop_loss_stop_price") or order.get("plan", {}).get("stop", 0.0))
        take_profit = float(order.get("take_profit_limit_price") or order.get("plan", {}).get("target", 0.0))
        notional = float(res0.get("value_usd", 0.0))
        planned_risk = float(res0.get("max_loss", 0.0))

        # 3. Create persistent DB record
        req_id = str(uuid.uuid4())
        app_req = ApprovalRequest(
            id=req_id,
            fingerprint=fingerprint,
            user_id=user_id,
            symbol=symbol,
            side=side,
            qty=qty,
            order_type=order_type,
            limit_price=limit_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            estimated_notional=notional,
            max_planned_risk=planned_risk,
            available_buying_power=buying_power,
            risk_verdict=verdict,
            status="PENDING",
            created_at=utcnow(),
            expires_at=expires_at,
            order_payload_json=json.dumps(order)
        )

        async with get_session() as session:
            repo = Repository(session)
            await repo.create_approval_request(app_req)
            await repo.log_audit("APPROVAL_CREATED", f"Order approval request {req_id} created for {symbol}", user_id)

        return True, app_req, "Order preview generated. Awaiting manual user approval."

    async def process_approval(
        self,
        approval_id: str,
        approving_user_id: int,
        now: Optional[datetime.datetime] = None
    ) -> Dict[str, Any]:
        """Step 5, 6, 7 & 8: Validate approval, execute on paper broker, and persist confirmation.

        Enforces all mandatory security criteria:
        1. Approving user authorization check.
        2. Idempotency and status check (Must be PENDING).
        3. Expiration check.
        4. Order integrity / fingerprint check.
        5. Re-check risk engine at the exact moment of approval.
        6. Validate paper broker account active.
        7. Execute paper order.
        8. Persist execution and broker response.
        """
        async with get_session() as session:
            repo = Repository(session)

            # 1. User authorization check
            is_auth = await repo.is_user_authorized(approving_user_id)
            if not is_auth:
                await repo.log_audit("UNAUTHORIZED_APPROVAL_ATTEMPT", f"User {approving_user_id} denied on {approval_id}", approving_user_id)
                raise ApprovalValidationError(f"Unauthorized: Telegram User ID {approving_user_id} is not authorized.")

            # 2. Approval existence and idempotency check
            req = await repo.get_approval_request(approval_id)
            if not req:
                raise ApprovalValidationError(f"Approval request {approval_id} not found.")

            if req.status != "PENDING":
                raise ApprovalValidationError(
                    f"Order cannot be approved: Status is already '{req.status}'. Duplicate submissions prevented."
                )

            # 3. Expiration check
            now_utc = utcnow()
            # Handle naive or aware datetime
            exp_time = req.expires_at
            if exp_time.tzinfo is None:
                exp_time = exp_time.replace(tzinfo=datetime.timezone.utc)
            if now_utc > exp_time:
                req.status = "EXPIRED"
                req.decided_at = now_utc
                await session.flush()
                await repo.log_audit("APPROVAL_EXPIRED", f"Approval {approval_id} expired", approving_user_id)
                raise ApprovalValidationError("This approval request has expired (5-minute TTL passed). Please generate a new trade.")

            # 4. Order integrity check
            order_dict = json.loads(req.order_payload_json)
            cur_fingerprint = self.ticket_adapter.calculate_fingerprint(order_dict)
            if cur_fingerprint != req.fingerprint:
                req.status = "REJECTED"
                await session.flush()
                raise ApprovalValidationError("Order integrity violation: Parameters altered since preview. Request rejected.")

            # 5. Re-check risk engine at execution time
            risk_check = self.risk_adapter.check_orders([order_dict], now=now)
            if risk_check["results"][0]["verdict"] != "PASS":
                reasons = " | ".join(risk_check["results"][0]["reasons"])
                req.status = "REJECTED"
                await session.flush()
                raise ApprovalValidationError(f"Risk re-check failed at approval time: {reasons}")

            # 6. Broker paper account verification
            broker = get_broker_instance()
            try:
                account = await broker.get_account()
                if not account.get("paper", False):
                    raise BrokerError("CRITICAL SECURITY ERROR: Broker account is not a verified paper account!")
                if account.get("status") != "ACTIVE":
                    raise BrokerError(f"Broker account status is {account.get('status')}, expected ACTIVE.")
            except Exception as e:
                logger.error("Broker verification failed: %s", e)
                raise ApprovalValidationError(f"Broker connection/verification error: {str(e)}")

            # 7. Execute Paper Order
            try:
                broker_res = await broker.submit_order(order_dict)
            except Exception as e:
                req.status = "FAILED"
                await session.flush()
                await repo.log_audit("ORDER_EXECUTION_FAILED", f"Broker rejected: {str(e)}", approving_user_id)
                raise ApprovalValidationError(f"Order submission rejected by broker: {str(e)}")

            # 8. Mark Approved and Persist Order Execution
            req.status = "APPROVED"
            req.decided_at = now_utc

            execution = OrderExecution(
                approval_id=req.id,
                broker_order_id=broker_res.get("broker_order_id"),
                client_order_id=broker_res.get("client_order_id", str(uuid.uuid4())),
                symbol=req.symbol,
                side=req.side,
                qty=req.qty,
                order_type=req.order_type,
                status=broker_res.get("status", "SUBMITTED"),
                submitted_at=now_utc,
                filled_avg_price=broker_res.get("filled_avg_price"),
                broker_response_json=json.dumps(broker_res)
            )
            await repo.create_order_execution(execution)
            await repo.log_audit(
                "ORDER_APPROVED_AND_EXECUTED",
                f"Paper order {broker_res.get('broker_order_id')} submitted for {req.qty} {req.symbol}",
                approving_user_id
            )

            return {
                "approval_id": req.id,
                "broker_order_id": broker_res.get("broker_order_id"),
                "symbol": req.symbol,
                "side": req.side.upper(),
                "qty": req.qty,
                "order_type": req.order_type.upper(),
                "limit_price": req.limit_price,
                "stop_loss": req.stop_loss,
                "take_profit": req.take_profit,
                "status": broker_res.get("status", "SUBMITTED").upper(),
                "submitted_at": broker_res.get("submitted_at"),
                "account_type": "Alpaca Paper Trading"
            }

    async def reject_approval(self, approval_id: str, user_id: int) -> bool:
        """Reject an order approval request."""
        async with get_session() as session:
            repo = Repository(session)
            is_auth = await repo.is_user_authorized(user_id)
            if not is_auth:
                raise ApprovalValidationError("Unauthorized user.")

            req = await repo.get_approval_request(approval_id)
            if not req:
                return False

            if req.status != "PENDING":
                raise ApprovalValidationError(f"Cannot reject order in '{req.status}' status.")

            req.status = "REJECTED"
            req.decided_at = utcnow()
            await session.flush()
            await repo.log_audit("APPROVAL_REJECTED", f"Order {approval_id} manually rejected by user {user_id}", user_id)
            return True
