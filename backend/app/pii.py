from __future__ import annotations

import hashlib


def hash_contact(value: str | None) -> str | None:
    if not value:
        return None
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"sha256:{digest}"


def last4_from_card(card: dict | None) -> str | None:
    if not card:
        return None
    last4 = card.get("last4")
    return str(last4) if last4 else None


def redact_event(raw: dict) -> dict:
    """Copy of a Razorpay-shaped event with contact hashed and PAN last4 only."""
    import copy

    body = copy.deepcopy(raw)
    payload = body.get("payload") or {}
    for key in ("payment", "checkout", "subscription"):
        entity = (payload.get(key) or {}).get("entity") or {}
        if "contact" in entity:
            entity["contact"] = hash_contact(entity.get("contact"))
        if "email" in entity and entity.get("email"):
            entity["email"] = hash_contact(entity["email"])
        if "vpa" in entity and entity.get("vpa"):
            vpa = str(entity["vpa"])
            entity["vpa"] = "***@" + vpa.split("@")[-1] if "@" in vpa else "***"
        notes = entity.get("notes")
        if isinstance(notes, dict) and "customer_name" in notes:
            notes["customer_name"] = "redacted"
    return body
