from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from app.config import DATA_DIR, get_settings
from app.pii import hash_contact, last4_from_card
from app.schemas import Consent, PolicyMode, RevenueAtRisk, SourceEvent

EVENT_MAP = {
    "payment.failed": SourceEvent.PAYMENT_FAILED,
    "payment.failed": SourceEvent.PAYMENT_FAILED,
    "checkout.abandoned": SourceEvent.CHECKOUT_ABANDONED,
    "subscription.pending": SourceEvent.SUBSCRIPTION_PENDING,
    "subscription.halted": SourceEvent.SUBSCRIPTION_HALTED,
}


def verify_webhook_signature(raw_body: bytes, signature: str | None) -> tuple[bool, str]:
    secret = get_settings().razorpay_webhook_secret
    if not secret:
        return True, "signature_skipped_demo"
    if not signature:
        return False, "missing_signature"
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if hmac.compare_digest(expected, signature):
        return True, "ok"
    return False, "mismatch"


def _entity(payload: dict, key: str) -> dict:
    node = payload.get(key) or {}
    if isinstance(node, dict) and "entity" in node:
        return node.get("entity") or {}
    return node if isinstance(node, dict) else {}


def _notes(entity: dict) -> dict[str, str]:
    notes = entity.get("notes") or {}
    if not isinstance(notes, dict):
        return {}
    return {str(k): str(v) for k, v in notes.items()}


def _truthy(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "yes"}


def normalize_event(raw: dict, policy_mode: PolicyMode = PolicyMode.BALANCED) -> RevenueAtRisk:
    event_name = raw.get("event") or ""
    source = EVENT_MAP.get(event_name)
    if source is None:
        raise ValueError(f"unsupported event type: {event_name}")

    payload = raw.get("payload") or {}
    payment = _entity(payload, "payment")
    checkout = _entity(payload, "checkout")
    subscription = _entity(payload, "subscription")
    primary = payment or checkout or subscription
    notes = _notes(payment) or _notes(checkout) or _notes(subscription)
    card = payment.get("card") if isinstance(payment.get("card"), dict) else None

    return RevenueAtRisk(
        event_id=str(raw.get("id") or primary.get("id")),
        source_event=source,
        payment_id=payment.get("id"),
        order_id=payment.get("order_id") or checkout.get("order_id"),
        subscription_id=subscription.get("id") or notes.get("subscription_id"),
        amount_paise=int(primary.get("amount") or 0),
        currency=primary.get("currency") or "INR",
        method=primary.get("method") or checkout.get("method_hint") or checkout.get("method_hint"),
        error_code=payment.get("error_code"),
        error_source=payment.get("error_source"),
        error_step=payment.get("error_step"),
        error_reason=payment.get("error_reason"),
        error_description=payment.get("error_description"),
        contact_hash=hash_contact(primary.get("contact")),
        email_hash=hash_contact(primary.get("email")),
        customer_id=notes.get("customer_id") or subscription.get("customer_id"),
        last4=last4_from_card(card),
        attempt_n=int(notes.get("attempt_n") or 1),
        consent=Consent(
            whatsapp=_truthy(notes.get("consent_whatsapp")),
            opted_out=_truthy(notes.get("opted_out")),
        ),
        subscription_state=subscription.get("status"),
        policy_mode=policy_mode,
        notes_flags=notes,
    )


def load_sample_batch() -> list[dict[str, Any]]:
    path = DATA_DIR / "batch_50.json"
    if not path.exists():
        path = DATA_DIR / "batch_50.json"
    return json.loads(path.read_text(encoding="utf-8"))
