"""Generate the gold 50-event batch in Razorpay webhook shape."""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
ACCOUNT = "acc_PayRecoverDemo"
CREATED = 1724323800

EVENTS: list[dict] = []
GOLD: dict[str, dict] = {}


def envelope(event_id: str, event: str, contains: list[str], payload: dict) -> dict:
    return {
        "id": event_id,
        "entity": "event",
        "account_id": ACCOUNT,
        "event": event,
        "contains": contains,
        "payload": payload,
        "created_at": CREATED,
    }


def card_obj(last4: str, network: str = "Visa") -> dict:
    return {
        "id": f"card_{last4}xPayR",
        "entity": "card",
        "name": "",
        "last4": last4,
        "network": network,
        "type": "debit",
        "issuer": "HDFC",
        "international": False,
        "emi": False,
    }


def note_obj(
    customer_id: str,
    product: str,
    name: str,
    consent: bool = True,
    attempt_n: int = 1,
    extra: dict | None = None,
) -> dict:
    body = {
        "customer_id": customer_id,
        "product": product,
        "customer_name": name,
        "consent_whatsapp": "true" if consent else "false",
        "opted_out": "false",
        "attempt_n": str(attempt_n),
        "locale": "en",
    }
    if extra:
        body.update(extra)
    return body


def payment_entity(
    *,
    pay_id: str,
    amount: int,
    method: str,
    email: str,
    contact: str,
    error_code: str,
    error_description: str,
    error_source: str,
    error_step: str,
    error_reason: str,
    order_id: str,
    notes: dict,
    vpa: str | None = None,
    card: dict | None = None,
    bank: str | None = None,
) -> dict:
    body: dict = {
        "id": pay_id,
        "entity": "payment",
        "amount": amount,
        "currency": "INR",
        "status": "failed",
        "order_id": order_id,
        "invoice_id": None,
        "international": False,
        "method": method,
        "amount_refunded": 0,
        "refund_status": None,
        "captured": False,
        "description": notes.get("product"),
        "card_id": card["id"] if card else None,
        "bank": bank,
        "wallet": None,
        "vpa": vpa,
        "email": email,
        "contact": contact,
        "notes": notes,
        "fee": None,
        "tax": None,
        "error_code": error_code,
        "error_description": error_description,
        "error_source": error_source,
        "error_step": error_step,
        "error_reason": error_reason,
        "created_at": CREATED,
    }
    if card:
        body["card"] = card
    return body


def record(event: dict, klass: str, allow: list[str], bucket: str) -> None:
    EVENTS.append(event)
    GOLD[event["id"]] = {"class": klass, "allow_actions": allow, "bucket": bucket}


def payment_failed(
    eid: str,
    amount: int,
    method: str,
    name: str,
    contact: str,
    email: str,
    product: str,
    error_code: str,
    error_description: str,
    error_source: str,
    error_step: str,
    error_reason: str,
    klass: str,
    allow: list[str],
    bucket: str,
    consent: bool = True,
    attempt_n: int = 1,
    extra_notes: dict | None = None,
    vpa: str | None = None,
    card: dict | None = None,
    bank: str | None = None,
    event_name: str = "payment.failed",
) -> None:
    record(
        envelope(
            eid,
            event_name,
            ["payment"],
            {
                "payment": {
                    "entity": payment_entity(
                        pay_id=f"pay_{eid[4:]}",
                        amount=amount,
                        method=method,
                        email=email,
                        contact=contact,
                        error_code=error_code,
                        error_description=error_description,
                        error_source=error_source,
                        error_step=error_step,
                        error_reason=error_reason,
                        order_id=f"order_{eid[4:]}",
                        notes=note_obj(
                            f"cust_{eid[4:]}",
                            product,
                            name,
                            consent=consent,
                            attempt_n=attempt_n,
                            extra=extra_notes,
                        ),
                        vpa=vpa,
                        card=card,
                        bank=bank,
                    )
                }
            },
        ),
        klass,
        allow,
        bucket,
    )


def build() -> None:
    EVENTS.clear()
    GOLD.clear()

    upi_timeout = [
        ("evt_UT01", 19900, "Aarav Shah", "aarav@okicici", "D2C snack box"),
        ("evt_UT02", 49900, "Diya Mehta", "diya@okaxis", "Yoga membership"),
        ("evt_UT03", 129900, "Kabir Iyer", "kabir@ybl", "Online course"),
        ("evt_UT04", 79900, "Ananya Rao", "ananya@oksbi", "SaaS monthly"),
        ("evt_UT05", 24900, "Ishaan Kapoor", "ishaan@paytm", "Clinic copay"),
        ("evt_UT06", 349900, "Meera Nair", "meera@okhdfcbank", "Annual plan"),
        ("evt_UT07", 9900, "Rohan Gupta", "rohan@ibl", "Add-on seat"),
        ("evt_UT08", 159900, "Sara Khan", "sara@okicici", "Flight hold"),
        ("evt_UT09", 59900, "Vikram Joshi", "vikram@okaxis", "Gym quarterly"),
        ("evt_UT10", 219900, "Priya Desai", "priya@ybl", "Laptop EMI down"),
        ("evt_UT11", 39900, "Arjun Bhat", "arjun@oksbi", "Prepaid wallet"),
        ("evt_UT12", 89900, "Nisha Verma", "nisha@okaxis", "Hotel hold"),
    ]
    for i, (eid, amount, name, vpa, product) in enumerate(upi_timeout, start=1):
        payment_failed(
            eid,
            amount,
            "upi",
            name,
            f"+9198110000{i:02d}",
            f"{name.split()[0].lower()}@example.com",
            product,
            "GATEWAY_ERROR",
            "Payment processing failed because of a technical error at the gateway.",
            "gateway",
            "payment_authorization",
            "gateway_technical_error",
            "upi_timeout",
            ["retry_same_method", "switch_method_upi", "issue_payment_link"],
            "recommend",
            vpa=vpa,
        )

    nsf = [
        ("evt_NSF01", 249900, "card", "Neel Sharma", "Rent share"),
        ("evt_NSF02", 79900, "upi", "Kavya Menon", "Course installment"),
        ("evt_NSF03", 159900, "upi", "Harsh Patel", "Insurance premium"),
        ("evt_NSF04", 49900, "card", "Ritu Agarwal", "SaaS monthly"),
        ("evt_NSF05", 329900, "netbanking", "Amit Kulkarni", "School fees"),
        ("evt_NSF06", 19900, "upi", "Pooja Jain", "D2C refill"),
        ("evt_NSF07", 89900, "upi", "Dev Reddy", "Broadband bill"),
        ("evt_NSF08", 119900, "card", "Sneha Iyer", "Clinic package"),
    ]
    for i, (eid, amount, method, name, product) in enumerate(nsf, start=1):
        payment_failed(
            eid,
            amount,
            method,
            name,
            f"+9198220000{i:02d}",
            f"{name.split()[0].lower()}@example.com",
            product,
            "BAD_REQUEST_ERROR",
            "Payment failed due to insufficient funds in the customer account.",
            "customer",
            "payment_authorization",
            "insufficient_funds",
            "insufficient_funds",
            ["schedule_delay_retry", "email_nudge", "whatsapp_nudge", "issue_payment_link"],
            "recommend",
            consent=eid != "evt_NSF08",
            vpa=f"{name.split()[0].lower()}@okicici" if method == "upi" else None,
            card=card_obj("4242") if method == "card" else None,
            bank="HDFC" if method == "netbanking" else None,
        )

    declines = [
        ("evt_CD01", 459900, "issuer_declined", "Visa", "1111", "Rahul Bose", "Camera body"),
        ("evt_CD02", 29900, "do_not_honor", "Mastercard", "4444", "Tanya Singh", "Makeup kit"),
        ("evt_CD03", 189900, "card_declined", "Visa", "5555", "Manish Rao", "Watch"),
        ("evt_CD04", 64900, "transaction_not_allowed", "RuPay", "2222", "Lata Pillai", "Headphones"),
        ("evt_CD05", 99900, "issuer_declined", "Visa", "8888", "Omar Sheikh", "Airline seat"),
        ("evt_CD06", 54900, "card_declined", "Mastercard", "0007", "Geeta Shah", "Kitchen appliance"),
    ]
    for i, (eid, amount, reason, network, last4, name, product) in enumerate(declines, start=1):
        payment_failed(
            eid,
            amount,
            "card",
            name,
            f"+9198330000{i:02d}",
            f"{name.split()[0].lower()}@example.com",
            product,
            "BAD_REQUEST_ERROR",
            "The issuing bank declined this card transaction.",
            "issuer",
            "payment_authorization",
            reason,
            "card_declined",
            ["issue_payment_link", "switch_method_upi", "email_nudge", "whatsapp_nudge"],
            "recommend",
            card=card_obj(last4, network),
        )

    otp = [
        ("evt_OTP01", 39900, "invalid_otp", "upi", "Siddharth Jain", "UPI collect"),
        ("evt_OTP02", 149900, "incorrect_otp", "card", "Alia Fernandes", "Card checkout"),
        ("evt_OTP03", 24900, "authentication_failed", "upi", "Varun Sethi", "Wallet top-up"),
        ("evt_OTP04", 79900, "user_dropped_authentication", "upi", "Rhea Kapoor", "Checkout OTP"),
        ("evt_OTP05", 119900, "invalid_otp", "card", "Kunal Bose", "EMI auth"),
    ]
    for i, (eid, amount, reason, method, name, product) in enumerate(otp, start=1):
        payment_failed(
            eid,
            amount,
            method,
            name,
            f"+9198440000{i:02d}",
            f"{name.split()[0].lower()}@example.com",
            product,
            "BAD_REQUEST_ERROR",
            "Authentication failed due to incorrect OTP.",
            "customer",
            "payment_authentication",
            reason,
            "auth_failed",
            ["email_nudge", "whatsapp_nudge", "issue_payment_link"],
            "recommend",
            consent=eid != "evt_OTP04",
            vpa=f"{name.split()[0].lower()}@ybl" if method == "upi" else None,
            card=card_obj("0153") if method == "card" else None,
        )

    abandon = [
        ("evt_AB01", 45900, "upi", "Yash Malhotra", "Cart: protein + shaker"),
        ("evt_AB02", 129900, "card", "Ira Banerjee", "Cart: annual plan"),
        ("evt_AB03", 21900, "upi", "Farhan Qureshi", "Cart: t-shirt"),
        ("evt_AB04", 89900, "upi", "Simran Kaur", "Cart: two skincare kits"),
        ("evt_AB05", 159900, "card", "Nikhil Rao", "Cart: noise-cancel headphones"),
    ]
    for i, (eid, amount, method, name, product) in enumerate(abandon, start=1):
        first = name.split()[0].lower()
        record(
            envelope(
                eid,
                "checkout.abandoned",
                ["checkout"],
                {
                    "checkout": {
                        "entity": {
                            "id": f"chk_{eid[4:]}",
                            "order_id": f"order_{eid[4:]}",
                            "amount": amount,
                            "currency": "INR",
                            "method_hint": method,
                            "status": "abandoned",
                            "email": f"{first}@example.com",
                            "contact": f"+9198550000{i:02d}",
                            "notes": note_obj(
                                f"cust_{eid[4:]}",
                                product,
                                name,
                                consent=eid != "evt_AB03",
                                extra={"minutes_idle": "18"},
                            ),
                            "abandoned_at": CREATED,
                        }
                    }
                },
            ),
            "checkout_abandoned",
            ["issue_payment_link", "whatsapp_nudge", "email_nudge"],
            "recommend",
        )

    pending = [
        ("evt_SP01", "sub_SP01", 79900, "Aditi Rao", "Pro monthly"),
        ("evt_SP02", "sub_SP02", 149900, "Mohit Jain", "Family plan"),
        ("evt_SP03", "sub_SP03", 49900, "Leela Nair", "Creator plan"),
    ]
    for i, (eid, sub, amount, name, product) in enumerate(pending, start=1):
        first = name.split()[0].lower()
        pay = payment_entity(
            pay_id=f"pay_{eid[4:]}",
            amount=amount,
            method="card",
            email=f"{first}@example.com",
            contact=f"+9198660000{i:02d}",
            error_code="BAD_REQUEST_ERROR",
            error_description="Auto-charge failed. Subscription moved to pending.",
            error_source="issuer",
            error_step="payment_authorization",
            error_reason="card_declined",
            order_id=f"order_{eid[4:]}",
            notes=note_obj(
                f"cust_{eid[4:]}",
                product,
                name,
                extra={"subscription_id": sub},
            ),
            card=card_obj("0153"),
        )
        record(
            envelope(
                eid,
                "subscription.pending",
                ["subscription", "payment"],
                {
                    "subscription": {
                        "entity": {
                            "id": sub,
                            "entity": "subscription",
                            "status": "pending",
                            "plan_id": "plan_pro_monthly",
                            "total_count": 12,
                            "paid_count": 3,
                            "remaining_count": 9,
                            "customer_id": f"cust_{eid[4:]}",
                        }
                    },
                    "payment": {"entity": pay},
                },
            ),
            "subscription_pending",
            ["retry_same_method", "update_mandate", "issue_payment_link"],
            "recommend",
        )

    halted = [
        ("evt_SH01", "sub_SH01", 79900, "Gaurav Kumar", "Pro monthly"),
        ("evt_SH02", "sub_SH02", 199900, "Bhavna Shah", "Studio plan"),
    ]
    for i, (eid, sub, amount, name, product) in enumerate(halted, start=1):
        first = name.split()[0].lower()
        pay = payment_entity(
            pay_id=f"pay_{eid[4:]}",
            amount=amount,
            method="card",
            email=f"{first}@example.com",
            contact=f"+9198770000{i:02d}",
            error_code="BAD_REQUEST_ERROR",
            error_description="All automatic retries exhausted. Subscription halted.",
            error_source="issuer",
            error_step="payment_authorization",
            error_reason="card_declined",
            order_id=f"order_{eid[4:]}",
            notes=note_obj(
                f"cust_{eid[4:]}",
                product,
                name,
                attempt_n=4,
                extra={"subscription_id": sub},
            ),
            card=card_obj("9999"),
        )
        record(
            envelope(
                eid,
                "subscription.halted",
                ["subscription", "payment"],
                {
                    "subscription": {
                        "entity": {
                            "id": sub,
                            "entity": "subscription",
                            "status": "halted",
                            "plan_id": "plan_pro_monthly",
                            "total_count": 12,
                            "paid_count": 4,
                            "remaining_count": 8,
                            "customer_id": f"cust_{eid[4:]}",
                        }
                    },
                    "payment": {"entity": pay},
                },
            ),
            "subscription_halted",
            ["escalate_human", "update_mandate", "issue_payment_link"],
            "escalate",
        )

    revoked = [
        ("evt_MR01", 79900, "mandate_revoked", "Pankaj Singh", "Pro monthly"),
        ("evt_MR02", 49900, "cancelled_by_customer", "Chitra Menon", "News pass"),
        ("evt_MR03", 129900, "emandate_cancelled", "Ravi Pillai", "Gym annual"),
    ]
    for i, (eid, amount, reason, name, product) in enumerate(revoked, start=1):
        payment_failed(
            eid,
            amount,
            "emandate",
            name,
            f"+9198880000{i:02d}",
            f"{name.split()[0].lower()}@example.com",
            product,
            "BAD_REQUEST_ERROR",
            "Customer cancelled the mandate from their bank.",
            "customer",
            "payment_authorization",
            reason,
            "mandate_revoked",
            ["escalate_human"],
            "escalate",
            extra_notes={"subscription_id": f"sub_{eid[4:]}"},
            bank="HDFC",
        )

    dnr = [
        ("evt_DNR01", 89900, "stolen_or_lost_card", "card", "Fraud desk case A"),
        ("evt_DNR02", 259900, "suspected_fraud", "upi", "Velocity spike case"),
        ("evt_DNR03", 149900, "bank_account_blocked", "netbanking", "Blocked account"),
    ]
    for i, (eid, amount, reason, method, product) in enumerate(dnr, start=1):
        payment_failed(
            eid,
            amount,
            method,
            "Redacted",
            f"+9198990000{i:02d}",
            "risk.review@example.com",
            product,
            "BAD_REQUEST_ERROR",
            "Payment blocked. Do not retry this instrument.",
            "issuer" if method != "upi" else "bank",
            "payment_authorization",
            reason,
            "do_not_retry",
            ["stop"],
            "policy_stop",
            consent=False,
            extra_notes={"risk_flag": "true"},
            card=card_obj("0000") if method == "card" else None,
            vpa="redacted@okicici" if method == "upi" else None,
            bank="HDFC" if method == "netbanking" else None,
        )

    resolved = [
        ("evt_AR01", 49900, "payment_already_processed", {}),
        ("evt_AR02", 79900, "duplicate_payment", {}),
        ("evt_AR03", 129900, "gateway_technical_error", {"already_captured": "true"}),
    ]
    for i, (eid, amount, reason, extra) in enumerate(resolved, start=1):
        payment_failed(
            eid,
            amount,
            "upi",
            "Resolved User",
            f"+9198000000{i:02d}",
            "resolved@example.com",
            "Already captured order",
            "BAD_REQUEST_ERROR" if reason != "gateway_technical_error" else "GATEWAY_ERROR",
            "Payment already processed or later captured.",
            "business",
            "payment_capture",
            reason,
            "already_resolved",
            ["stop"],
            "recommend",
            extra_notes=extra,
            vpa="resolved@ybl",
        )


def main() -> None:
    build()
    DATA.mkdir(parents=True, exist_ok=True)
    if len(EVENTS) != 50:
        raise SystemExit(f"expected 50 events, got {len(EVENTS)}")
    buckets = {"recommend": 0, "escalate": 0, "policy_stop": 0}
    for g in GOLD.values():
        buckets[g["bucket"]] += 1
    if buckets != {"recommend": 42, "escalate": 5, "policy_stop": 3}:
        raise SystemExit(f"unexpected gold buckets: {buckets}")
    (DATA / "batch_50.json").write_text(json.dumps(EVENTS, indent=2), encoding="utf-8")
    (DATA / "gold.json").write_text(json.dumps(GOLD, indent=2), encoding="utf-8")
    print(f"wrote {len(EVENTS)} events -> {DATA / 'batch_50.json'}")
    print(f"gold buckets: {buckets}")


if __name__ == "__main__":
    main()
