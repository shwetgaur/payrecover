from __future__ import annotations

import json
import uuid

from sqlalchemy.orm import Session

from app.config import get_settings
from app.faults import get_faults
from app.graph import run_agent
from app.ingest import load_sample_batch, normalize_event, verify_webhook_signature
from app.models import AuditEntry, Case, Run, SeenEvent
from app.schemas import (
    AuditOut,
    CaseOut,
    Locale,
    MetricsOut,
    PolicyMode,
    RunOut,
    RunRequest,
)


def _bucket(diagnosis_class: str, action: str) -> str:
    if diagnosis_class == "do_not_retry" and action == "stop":
        return "policy_stop"
    if action == "escalate_human":
        return "escalate"
    return "recommend"


def _metrics(cases: list[Case], degraded: bool) -> MetricsOut:
    at_risk = sum(c.amount_paise for c in cases)
    recovered = sum(c.recovered_paise for c in cases)
    return MetricsOut(
        at_risk_paise=at_risk,
        recovered_paise=recovered,
        recovery_rate=(recovered / at_risk) if at_risk else 0.0,
        recommended_count=sum(1 for c in cases if c.bucket == "recommend"),
        escalated_count=sum(1 for c in cases if c.bucket == "escalate"),
        stopped_count=sum(1 for c in cases if c.bucket == "policy_stop"),
        queued_count=sum(1 for c in cases if c.outcome == "queued"),
        policy_violations=0,
        case_count=len(cases),
        degraded=degraded,
    )


def _case_out(case: Case, include_audit: bool = True) -> CaseOut:
    audits = []
    if include_audit:
        audits = [
            AuditOut(
                ts=row.ts.isoformat(),
                actor=row.actor,
                event_type=row.event_type,
                severity=row.severity,
                payload=json.loads(row.payload_json or "{}"),
            )
            for row in case.audits
        ]
    return CaseOut(
        id=case.id,
        run_id=case.run_id,
        event_id=case.event_id,
        payment_id=case.payment_id,
        order_id=case.order_id,
        source_event=case.source_event,
        amount_paise=case.amount_paise,
        method=case.method,
        diagnosis_class=case.diagnosis_class,
        diagnosis_rationale=case.diagnosis_rationale,
        diagnosis_source=case.diagnosis_source,
        action=case.action,
        channel=case.channel,
        outcome=case.outcome,
        recovered_paise=case.recovered_paise,
        bucket=case.bucket,
        degraded=case.degraded,
        message_en=case.message_en,
        message_hinglish=case.message_hinglish,
        policy_reasons=json.loads(case.policy_reasons_json or "[]"),
        audit=audits,
        revenue_at_risk=json.loads(case.revenue_json or "{}"),
    )


def _run_out(run: Run, include_cases: bool = False) -> RunOut:
    cases = list(run.cases)
    return RunOut(
        id=run.id,
        created_at=run.created_at.isoformat(),
        policy_mode=run.policy_mode,
        locale=run.locale,
        status=run.status,
        metrics=_metrics(cases, run.degraded),
        llm_mode=run.llm_mode,
        case_ids=[c.id for c in cases],
        cases=[_case_out(c) for c in cases] if include_cases else None,
    )


def process_event(
    db: Session,
    raw: dict,
    run: Run,
    *,
    llm_down: bool,
    whatsapp_timeout: bool,
    locale: Locale,
    policy_mode: PolicyMode,
    skip_if_seen: bool = False,
) -> Case:
    rar = normalize_event(raw, policy_mode)
    if skip_if_seen:
        seen = db.get(SeenEvent, rar.event_id)
        if seen:
            existing = db.get(Case, seen.case_id)
            if existing:
                return existing

    result = run_agent(rar, llm_down=llm_down, whatsapp_timeout=whatsapp_timeout, locale=locale)
    diagnosis = result.get("diagnosis") or {}
    plan = result.get("plan") or {}
    policy = result.get("policy") or {}
    outcome = result.get("outcome") or {}
    msg_en = result.get("message_en") or {}
    msg_hi = result.get("message_hinglish") or {}
    action = plan.get("action") or "stop"
    klass = diagnosis.get("klass") or "unknown"
    case = Case(
        id=f"case_{uuid.uuid4().hex[:12]}",
        run_id=run.id,
        event_id=rar.event_id,
        payment_id=rar.payment_id,
        order_id=rar.order_id,
        source_event=rar.source_event.value,
        amount_paise=rar.amount_paise,
        method=rar.method,
        diagnosis_class=klass,
        diagnosis_rationale=diagnosis.get("rationale"),
        diagnosis_source=diagnosis.get("source"),
        action=action,
        channel=plan.get("channel"),
        outcome=outcome.get("status"),
        recovered_paise=int(outcome.get("recovered_paise") or 0),
        bucket=_bucket(klass, action),
        degraded=bool(result.get("degraded")),
        message_en=msg_en.get("body"),
        message_hinglish=msg_hi.get("body"),
        policy_reasons_json=json.dumps(policy.get("reasons") or []),
        revenue_json=rar.model_dump_json(),
        raw_event_json=json.dumps(raw),
    )
    db.add(case)
    for row in result.get("audit") or []:
        db.add(
            AuditEntry(
                case_id=case.id,
                run_id=run.id,
                actor=row.get("actor") or "agent",
                event_type=row.get("event_type") or "event",
                severity=row.get("severity") or "info",
                payload_json=json.dumps(row.get("payload") or {}),
            )
        )
    db.merge(SeenEvent(event_id=rar.event_id, case_id=case.id))
    return case


def run_batch(db: Session, req: RunRequest, events: list[dict] | None = None) -> RunOut:
    faults = get_faults(db)
    llm_down = faults.llm == "down"
    whatsapp_timeout = faults.whatsapp == "timeout"
    llm_mode = "fallback" if llm_down or not get_settings().groq_api_key else "live"
    run = Run(
        id=f"run_{uuid.uuid4().hex[:12]}",
        policy_mode=req.policy_mode.value,
        locale=req.locale.value,
        status="running",
        llm_mode=llm_mode,
        degraded=llm_down or whatsapp_timeout,
    )
    db.add(run)
    db.flush()
    payload = events if events is not None else load_sample_batch()
    cases = [
        process_event(
            db,
            raw,
            run,
            llm_down=llm_down,
            whatsapp_timeout=whatsapp_timeout,
            locale=req.locale,
            policy_mode=req.policy_mode,
        )
        for raw in payload
    ]
    metrics = _metrics(cases, run.degraded)
    run.at_risk_paise = metrics.at_risk_paise
    run.recovered_paise = metrics.recovered_paise
    run.recommended_count = metrics.recommended_count
    run.escalated_count = metrics.escalated_count
    run.stopped_count = metrics.stopped_count
    run.queued_count = metrics.queued_count
    run.policy_violations = metrics.policy_violations
    run.degraded = metrics.degraded
    run.status = "completed"
    db.commit()
    db.refresh(run)
    return _run_out(run, include_cases=True)


def ingest_webhook(db: Session, raw_body: bytes, signature: str | None) -> dict:
    ok, reason = verify_webhook_signature(raw_body, signature)
    if not ok:
        raise ValueError(reason)
    raw = json.loads(raw_body.decode("utf-8"))
    req = RunRequest()
    run = Run(
        id=f"run_{uuid.uuid4().hex[:12]}",
        policy_mode=req.policy_mode.value,
        locale=req.locale.value,
        status="running",
        llm_mode="live" if get_settings().groq_api_key else "fallback",
    )
    db.add(run)
    db.flush()
    faults = get_faults(db)
    process_event(
        db,
        raw,
        run,
        llm_down=faults.llm == "down",
        whatsapp_timeout=faults.whatsapp == "timeout",
        locale=req.locale,
        policy_mode=req.policy_mode,
        skip_if_seen=True,
    )
    run.status = "completed"
    db.commit()
    return {"run_id": run.id, "event_id": raw.get("id"), "status": "accepted"}


def latest_metrics(db: Session) -> MetricsOut:
    run = db.query(Run).order_by(Run.created_at.desc()).first()
    if not run:
        return MetricsOut(
            at_risk_paise=0,
            recovered_paise=0,
            recovery_rate=0.0,
            recommended_count=0,
            escalated_count=0,
            stopped_count=0,
            queued_count=0,
            policy_violations=0,
            case_count=0,
        )
    return _metrics(list(run.cases), run.degraded)


def get_run(db: Session, run_id: str) -> RunOut | None:
    run = db.get(Run, run_id)
    return _run_out(run, include_cases=True) if run else None


def get_case(db: Session, case_id: str) -> CaseOut | None:
    case = db.get(Case, case_id)
    return _case_out(case) if case else None
