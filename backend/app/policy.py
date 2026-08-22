from __future__ import annotations

from datetime import timedelta

from app.catalog import cooldown_minutes, default_action_for, is_forbidden
from app.clock import is_quiet_hours, next_send_window, now_ist
from app.schemas import ActionType, Diagnosis, PlannedAction, PolicyDecision, PolicyMode, RevenueAtRisk

CUSTOMER_TOUCH_ACTIONS = {
    ActionType.WHATSAPP_NUDGE,
    ActionType.EMAIL_NUDGE,
    ActionType.ISSUE_PAYMENT_LINK,
    ActionType.SWITCH_METHOD_UPI,
}
NEVER_RETRY = {"do_not_retry", "mandate_revoked", "already_resolved"}
STOP_CLASSES = {"do_not_retry", "already_resolved"}
ESCALATE_CLASSES = {"mandate_revoked", "subscription_halted"}


def preferred_action(diagnosis: Diagnosis, rar: RevenueAtRisk) -> ActionType:
    klass = diagnosis.klass
    mode = rar.policy_mode
    base = default_action_for(klass)
    if klass.value in STOP_CLASSES:
        return ActionType.STOP
    if klass.value in ESCALATE_CLASSES:
        return ActionType.ESCALATE_HUMAN
    if klass.value == "auth_failed":
        if mode != PolicyMode.CONSERVATIVE and rar.consent.whatsapp and not rar.consent.opted_out:
            return ActionType.WHATSAPP_NUDGE
        return ActionType.EMAIL_NUDGE
    if klass.value == "upi_timeout" and mode == PolicyMode.AGGRESSIVE:
        return ActionType.SWITCH_METHOD_UPI
    if klass.value == "insufficient_funds":
        return ActionType.SCHEDULE_DELAY_RETRY
    if mode == PolicyMode.CONSERVATIVE and base == ActionType.WHATSAPP_NUDGE:
        return ActionType.EMAIL_NUDGE
    return base


def apply_policy(
    rar: RevenueAtRisk,
    diagnosis: Diagnosis,
    desired: ActionType,
    prior_recovery_actions: int = 0,
    prior_touches_7d: int = 0,
) -> tuple[PolicyDecision, PlannedAction]:
    reasons: list[str] = []
    action = desired
    rewritten_from: ActionType | None = None

    if rar.consent.opted_out and action in CUSTOMER_TOUCH_ACTIONS:
        rewritten_from, action = action, ActionType.STOP
        reasons.append("opted_out")
    if action == ActionType.WHATSAPP_NUDGE and not rar.consent.whatsapp:
        rewritten_from, action = action, ActionType.EMAIL_NUDGE
        reasons.append("whatsapp_without_consent")
    if is_forbidden(diagnosis.klass, action) or (
        diagnosis.klass.value in NEVER_RETRY
        and action in {ActionType.RETRY_SAME_METHOD, ActionType.SWITCH_METHOD_UPI, ActionType.SCHEDULE_DELAY_RETRY}
    ):
        rewritten_from = action
        action = ActionType.STOP if diagnosis.klass.value in STOP_CLASSES else ActionType.ESCALATE_HUMAN
        reasons.append("never_retry_class")
    if prior_recovery_actions >= 2 and action not in {ActionType.STOP, ActionType.ESCALATE_HUMAN}:
        rewritten_from, action = action, ActionType.STOP
        reasons.append("max_recovery_actions")
    if prior_touches_7d >= 2 and action in CUSTOMER_TOUCH_ACTIONS:
        rewritten_from, action = action, ActionType.STOP
        reasons.append("max_customer_touches")
    if rar.attempt_n >= 4 and action == ActionType.RETRY_SAME_METHOD:
        rewritten_from, action = action, ActionType.ESCALATE_HUMAN
        reasons.append("retry_budget_exhausted")

    quiet = False
    execute_after = None
    if action in CUSTOMER_TOUCH_ACTIONS and is_quiet_hours():
        quiet = True
        execute_after = next_send_window().isoformat()
        reasons.append("quiet_hours_queued")

    cooldown = cooldown_minutes(diagnosis.klass)
    if action == ActionType.RETRY_SAME_METHOD and diagnosis.klass.value == "upi_timeout":
        execute_after = (now_ist() + timedelta(minutes=15)).isoformat()
        cooldown = 15
        reasons.append("upi_timeout_cooldown_15m")
    if action == ActionType.SCHEDULE_DELAY_RETRY:
        minutes = 36 * 60 if rar.policy_mode != PolicyMode.AGGRESSIVE else 24 * 60
        execute_after = (now_ist() + timedelta(minutes=minutes)).isoformat()
        cooldown = minutes
        reasons.append("payday_window")

    channel = {
        ActionType.WHATSAPP_NUDGE: "whatsapp",
        ActionType.EMAIL_NUDGE: "email",
        ActionType.ISSUE_PAYMENT_LINK: "payment_link",
        ActionType.SWITCH_METHOD_UPI: "upi_intent",
        ActionType.UPDATE_MANDATE: "hosted_mandate",
        ActionType.RETRY_SAME_METHOD: "retry",
        ActionType.SCHEDULE_DELAY_RETRY: "retry",
        ActionType.ESCALATE_HUMAN: "ops",
        ActionType.STOP: "none",
        ActionType.MARK_PROMISE_TO_PAY: "ops",
    }[action]
    stop_condition = {
        ActionType.STOP: "no_further_action",
        ActionType.ESCALATE_HUMAN: "human_owns_case",
        ActionType.RETRY_SAME_METHOD: "captured_or_second_failure",
        ActionType.SCHEDULE_DELAY_RETRY: "captured_or_window_elapsed",
        ActionType.ISSUE_PAYMENT_LINK: "link_paid_or_expired",
        ActionType.WHATSAPP_NUDGE: "reply_or_one_touch",
        ActionType.EMAIL_NUDGE: "reply_or_one_touch",
        ActionType.SWITCH_METHOD_UPI: "upi_success_or_fail",
        ActionType.UPDATE_MANDATE: "mandate_updated_or_declined",
        ActionType.MARK_PROMISE_TO_PAY: "promise_date_reached",
    }[action]
    decision = PolicyDecision(
        allowed=True,
        action=action,
        reasons=reasons or ["policy_pass"],
        queued_quiet_hours=quiet,
        rewritten_from=rewritten_from,
    )
    plan = PlannedAction(
        action=action,
        reason_code=diagnosis.klass.value,
        stop_condition=stop_condition,
        max_attempts=1,
        execute_after=execute_after,
        channel=channel,
        cooldown_minutes=cooldown,
    )
    return decision, plan


preferred_action = preferred_action
apply_policy = apply_policy
