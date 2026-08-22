from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from app.config import DATA_DIR
from app.schemas import ActionType, Diagnosis, DiagnosisClass, RevenueAtRisk

CLASS_BY_NAME = {c.value: c for c in DiagnosisClass}
ACTION_BY_NAME = {a.value: a for a in ActionType}


@lru_cache
def load_catalog() -> dict[str, Any]:
    return yaml.safe_load((DATA_DIR / "error_catalog.yaml").read_text(encoding="utf-8"))


def recovery_probability(klass: str, action: str) -> float:
    table = load_catalog().get("recovery_probability") or {}
    return float((table.get(klass) or {}).get(action) or 0.0)


def _rule_matches(rule: dict, rar: RevenueAtRisk) -> bool:
    when = rule.get("when") or {}
    if when.get("source_event") and when["source_event"] != rar.source_event.value:
        return False
    flag = when.get("notes_flag")
    if flag:
        raw = str((rar.notes_flags or {}).get(flag, "")).lower()
        if raw not in {"1", "true", "yes"}:
            return False
    reasons = when.get("error_reason")
    if reasons and (rar.error_reason or "") not in reasons:
        return False
    method = when.get("method")
    if method and (rar.method or "") != method:
        return False
    return bool(when)


def match_rule(rar: RevenueAtRisk) -> Diagnosis | None:
    for rule in load_catalog().get("rules") or []:
        if not _rule_matches(rule, rar):
            continue
        klass = CLASS_BY_NAME[rule["class"]]
        return Diagnosis(
            klass=klass,
            confidence="high",
            source="rules",
            rationale=rule.get("rationale") or "",
            matched_rule=rule.get("id"),
        )
    return None


def default_action_for(klass: DiagnosisClass) -> ActionType:
    for rule in load_catalog().get("rules") or []:
        if rule.get("class") == klass.value:
            action = rule.get("default_action")
            if action in ACTION_BY_NAME:
                return ACTION_BY_NAME[action]
    if klass == DiagnosisClass.DO_NOT_RETRY:
        return ActionType.STOP
    if klass in {DiagnosisClass.MANDATE_REVOKED, DiagnosisClass.SUBSCRIPTION_HALTED}:
        return ActionType.ESCALATE_HUMAN
    return ActionType.ESCALATE_HUMAN


def cooldown_minutes(klass: DiagnosisClass) -> int:
    for rule in load_catalog().get("rules") or []:
        if rule.get("class") == klass.value:
            return int(rule.get("cooldown_minutes") or 0)
    return 0


def is_forbidden(klass: DiagnosisClass, action: ActionType) -> bool:
    forbidden = (load_catalog().get("forbidden_actions") or {}).get(klass.value) or []
    return action.value in forbidden


match_rule = match_rule
default_action_for = default_action_for
cooldown_minutes = cooldown_minutes
is_forbidden = is_forbidden
