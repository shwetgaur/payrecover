from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class SourceEvent(str, Enum):
    PAYMENT_FAILED = "payment.failed"
    CHECKOUT_ABANDONED = "checkout.abandoned"
    SUBSCRIPTION_PENDING = "subscription.pending"
    SUBSCRIPTION_HALTED = "subscription.halted"


class DiagnosisClass(str, Enum):
    UPI_TIMEOUT = "upi_timeout"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    CARD_DECLINED = "card_declined"
    AUTH_FAILED = "auth_failed"
    EXPIRED_INSTRUMENT = "expired_instrument"
    MANDATE_REVOKED = "mandate_revoked"
    CHECKOUT_ABANDONED = "checkout_abandoned"
    SUBSCRIPTION_PENDING = "subscription_pending"
    SUBSCRIPTION_HALTED = "subscription_halted"
    DO_NOT_RETRY = "do_not_retry"
    ALREADY_RESOLVED = "already_resolved"
    UNKNOWN = "unknown"


class ActionType(str, Enum):
    RETRY_SAME_METHOD = "retry_same_method"
    ISSUE_PAYMENT_LINK = "issue_payment_link"
    SWITCH_METHOD_UPI = "switch_method_upi"
    UPDATE_MANDATE = "update_mandate"
    WHATSAPP_NUDGE = "whatsapp_nudge"
    EMAIL_NUDGE = "email_nudge"
    SCHEDULE_DELAY_RETRY = "schedule_delay_retry"
    MARK_PROMISE_TO_PAY = "mark_promise_to_pay"
    ESCALATE_HUMAN = "escalate_human"
    STOP = "stop"


class PolicyMode(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class Locale(str, Enum):
    EN = "en"
    HINGLISH = "hinglish"


class Consent(BaseModel):
    whatsapp: bool = False
    opted_out: bool = False


class RevenueAtRisk(BaseModel):
    event_id: str
    source_event: SourceEvent
    payment_id: str | None = None
    order_id: str | None = None
    subscription_id: str | None = None
    amount_paise: int
    currency: str = "INR"
    method: str | None = None
    error_code: str | None = None
    error_source: str | None = None
    error_step: str | None = None
    error_reason: str | None = None
    error_description: str | None = None
    contact_hash: str | None = None
    email_hash: str | None = None
    customer_id: str | None = None
    last4: str | None = None
    attempt_n: int = 1
    prior_actions: list[str] = Field(default_factory=list)
    consent: Consent = Field(default_factory=Consent)
    subscription_state: str | None = None
    policy_mode: PolicyMode = PolicyMode.BALANCED
    notes_flags: dict[str, str] = Field(default_factory=dict)


class Diagnosis(BaseModel):
    klass: DiagnosisClass
    confidence: Literal["high", "medium", "low"]
    source: Literal["rules", "groq", "fallback"]
    rationale: str
    matched_rule: str | None = None


class PlannedAction(BaseModel):
    action: ActionType
    reason_code: str
    stop_condition: str
    max_attempts: int = 1
    execute_after: str | None = None
    channel: str | None = None
    cooldown_minutes: int = 0


class PolicyDecision(BaseModel):
    allowed: bool
    action: ActionType
    reasons: list[str] = Field(default_factory=list)
    queued_quiet_hours: bool = False
    rewritten_from: ActionType | None = None


class CustomerMessage(BaseModel):
    locale: Locale
    channel: str
    subject: str
    body: str
    source: Literal["groq", "template"]


class ActionOutcome(BaseModel):
    status: Literal["recovered", "failed", "queued", "stopped", "escalated", "noop"]
    recovered_paise: int = 0
    simulated: bool = True
    probability: float = 0.0
    adapter: str
    detail: str
    degraded: bool = False


class FaultState(BaseModel):
    llm: Literal["up", "down"] = "up"
    whatsapp: Literal["ok", "timeout"] = "ok"


class RunRequest(BaseModel):
    source: Literal["sample_batch", "uploaded"] = "sample_batch"
    policy_mode: PolicyMode = PolicyMode.BALANCED
    locale: Locale = Locale.EN


class FaultRequest(BaseModel):
    llm: Literal["up", "down"] | None = None
    whatsapp: Literal["ok", "timeout"] | None = None


class MetricsOut(BaseModel):
    at_risk_paise: int
    recovered_paise: int
    recovery_rate: float
    recommended_count: int
    escalated_count: int
    stopped_count: int
    queued_count: int
    policy_violations: int
    case_count: int
    degraded: bool = False


class AuditOut(BaseModel):
    ts: str
    actor: str
    event_type: str
    severity: str
    payload: dict[str, Any]


class CaseOut(BaseModel):
    id: str
    run_id: str
    event_id: str
    payment_id: str | None
    order_id: str | None
    source_event: str
    amount_paise: int
    method: str | None
    diagnosis_class: str | None
    diagnosis_rationale: str | None
    diagnosis_source: str | None
    action: str | None
    channel: str | None
    outcome: str | None
    recovered_paise: int
    bucket: str | None
    degraded: bool
    message_en: str | None = None
    message_hinglish: str | None = None
    policy_reasons: list[str] = Field(default_factory=list)
    audit: list[AuditOut] = Field(default_factory=list)
    revenue_at_risk: dict[str, Any] | None = None


class RunOut(BaseModel):
    id: str
    created_at: str
    policy_mode: str
    locale: str
    status: str
    metrics: MetricsOut
    llm_mode: str
    case_ids: list[str] = Field(default_factory=list)
    cases: list[CaseOut] | None = None


# Compatibility aliases used by different modules.
SourceEvent = SourceEvent
DiagnosisClass = DiagnosisClass
PolicyMode = PolicyMode
PolicyDecision = PolicyDecision
CustomerMessage = CustomerMessage
RevenueAtRisk = RevenueAtRisk
PlannedAction = PlannedAction
