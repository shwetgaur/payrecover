from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.adapters import execute_action
from app.catalog import match_rule
from app.llm import classify_unknown, write_rationale
from app.messages import build_messages
from app.policy import apply_policy, preferred_action
from app.schemas import (
    ActionOutcome,
    Diagnosis,
    DiagnosisClass,
    Locale,
    PlannedAction,
    PolicyDecision,
    RevenueAtRisk,
)


class AgentState(TypedDict, total=False):
    rar: dict
    llm_down: bool
    whatsapp_timeout: bool
    locale: str
    diagnosis: dict
    policy: dict
    plan: dict
    message_en: dict
    message_hinglish: dict
    outcome: dict
    audit: list[dict]
    degraded: bool


def _audit(state: AgentState, actor: str, event_type: str, payload: dict, severity: str = "info") -> None:
    rows = list(state.get("audit") or [])
    rows.append({"actor": actor, "event_type": event_type, "severity": severity, "payload": payload})
    state["audit"] = rows


def diagnose_node(state: AgentState) -> AgentState:
    rar = RevenueAtRisk.model_validate(state["rar"])
    llm_down = bool(state.get("llm_down"))
    matched = match_rule(rar)
    degraded = bool(state.get("degraded"))
    if matched:
        rationale = write_rationale(rar, matched.klass, llm_down) or matched.rationale
        diagnosis = matched.model_copy(update={"rationale": rationale})
        if llm_down:
            degraded = True
            _audit(state, "diagnose", "llm_fallback", {"reason": "llm_down"}, "warn")
        _audit(state, "diagnose", "rule_match", diagnosis.model_dump())
    else:
        groq = classify_unknown(rar, llm_down)
        if groq:
            diagnosis = groq
            _audit(state, "diagnose", "groq_classify", diagnosis.model_dump())
        else:
            diagnosis = Diagnosis(
                klass=DiagnosisClass.UNKNOWN,
                confidence="low",
                source="fallback",
                rationale="No catalog rule matched and LLM was unavailable. Escalate.",
            )
            degraded = True
            _audit(state, "diagnose", "fallback_escalate", diagnosis.model_dump(), "warn")
    state["diagnosis"] = diagnosis.model_dump()
    state["degraded"] = degraded
    return state


def policy_node(state: AgentState) -> AgentState:
    rar = RevenueAtRisk.model_validate(state["rar"])
    diagnosis = Diagnosis.model_validate(state["diagnosis"])
    desired = preferred_action(diagnosis, rar)
    decision, plan = apply_policy(rar, diagnosis, desired)
    _audit(
        state,
        "policy",
        "gate",
        {"desired": desired.value, "decision": decision.model_dump(), "plan": plan.model_dump()},
        "info" if decision.allowed else "block",
    )
    state["policy"] = decision.model_dump()
    state["plan"] = plan.model_dump()
    return state


def compose_node(state: AgentState) -> AgentState:
    rar = RevenueAtRisk.model_validate(state["rar"])
    diagnosis = Diagnosis.model_validate(state["diagnosis"])
    plan = PlannedAction.model_validate(state["plan"])
    llm_down = bool(state.get("llm_down"))
    en, hi = build_messages(rar, plan, diagnosis.klass.value, llm_down)
    _audit(state, "compose", "messages", {"en": en.model_dump(), "hinglish": hi.model_dump()})
    state["message_en"] = en.model_dump()
    state["message_hinglish"] = hi.model_dump()
    if llm_down:
        state["degraded"] = True
    return state


def act_node(state: AgentState) -> AgentState:
    rar = RevenueAtRisk.model_validate(state["rar"])
    diagnosis = Diagnosis.model_validate(state["diagnosis"])
    plan = PlannedAction.model_validate(state["plan"])
    policy = PolicyDecision.model_validate(state["policy"])
    outcome = execute_action(
        rar,
        diagnosis.klass.value,
        plan,
        whatsapp_timeout=bool(state.get("whatsapp_timeout")),
        quiet_queued=policy.queued_quiet_hours,
    )
    if outcome.degraded:
        state["degraded"] = True
        _audit(state, "act", "degraded", outcome.model_dump(), "degraded")
    else:
        _audit(state, "act", "executed", outcome.model_dump())
    state["outcome"] = outcome.model_dump()
    return state


def observe_node(state: AgentState) -> AgentState:
    outcome = ActionOutcome.model_validate(state["outcome"])
    _audit(state, "observe", "outcome", {"status": outcome.status, "recovered_paise": outcome.recovered_paise})
    return state


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("diagnose", diagnose_node)
    graph.add_node("policy", policy_node)
    graph.add_node("compose", compose_node)
    graph.add_node("act", act_node)
    graph.add_node("observe", observe_node)
    graph.set_entry_point("diagnose")
    graph.add_edge("diagnose", "policy")
    graph.add_edge("policy", "compose")
    graph.add_edge("compose", "act")
    graph.add_edge("act", "observe")
    graph.add_edge("observe", END)
    return graph.compile()


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH


def run_agent(
    rar: RevenueAtRisk,
    *,
    llm_down: bool,
    whatsapp_timeout: bool,
    locale: Locale = Locale.EN,
) -> dict[str, Any]:
    initial: AgentState = {
        "rar": rar.model_dump(),
        "llm_down": llm_down,
        "whatsapp_timeout": whatsapp_timeout,
        "locale": locale.value,
        "audit": [],
        "degraded": False,
    }
    return dict(get_graph().invoke(initial))
