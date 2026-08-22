from __future__ import annotations

import hashlib

from app.catalog import recovery_probability
from app.schemas import ActionOutcome, ActionType, PlannedAction, RevenueAtRisk


def _unit_random(event_id: str) -> float:
    return int(hashlib.sha256(event_id.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF


def execute_action(
    rar: RevenueAtRisk,
    klass: str,
    plan: PlannedAction,
    whatsapp_timeout: bool,
    quiet_queued: bool = False,
) -> ActionOutcome:
    action = plan.action
    if action == ActionType.STOP:
        return ActionOutcome(status="stopped", adapter="policy", detail="Policy stop. No adapter invoked.")
    if action == ActionType.ESCALATE_HUMAN:
        return ActionOutcome(
            status="escalated",
            adapter="ops_queue",
            detail="Escalated to human ops with update-method recommendation.",
        )
    p = recovery_probability(klass, action.value)
    if action == ActionType.WHATSAPP_NUDGE and whatsapp_timeout:
        return ActionOutcome(
            status="queued",
            probability=p,
            adapter="whatsapp",
            detail="WhatsApp adapter timed out. Action queued. Case continues.",
            degraded=True,
        )
    if quiet_queued:
        return ActionOutcome(
            status="queued",
            probability=p,
            adapter=plan.channel or "queue",
            detail=f"Quiet hours. Send after {plan.execute_after}.",
        )
    adapter = {
        ActionType.RETRY_SAME_METHOD: "razorpay_retry_sim",
        ActionType.SCHEDULE_DELAY_RETRY: "razorpay_retry_sim",
        ActionType.ISSUE_PAYMENT_LINK: "payment_link_sim",
        ActionType.SWITCH_METHOD_UPI: "upi_intent_sim",
        ActionType.UPDATE_MANDATE: "hosted_mandate_sim",
        ActionType.EMAIL_NUDGE: "email_sim",
        ActionType.WHATSAPP_NUDGE: "whatsapp_sim",
        ActionType.MARK_PROMISE_TO_PAY: "ops_queue",
    }.get(action, "sim")
    hit = _unit_random(rar.event_id) < p
    if hit:
        return ActionOutcome(
            status="recovered",
            recovered_paise=rar.amount_paise,
            probability=p,
            adapter=adapter,
            detail=f"Simulated success using p={p:.2f} (seed=event_id).",
        )
    return ActionOutcome(
        status="failed",
        probability=p,
        adapter=adapter,
        detail=f"Simulated miss using p={p:.2f} (seed=event_id).",
    )


execute_action = execute_action
