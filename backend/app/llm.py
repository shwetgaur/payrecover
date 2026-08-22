from __future__ import annotations

import json
import logging

from app.config import get_settings
from app.schemas import Diagnosis, DiagnosisClass, Locale, RevenueAtRisk

log = logging.getLogger("payrecover.llm")
CLASS_LIST = ", ".join(c.value for c in DiagnosisClass)


def groq_available(llm_down: bool) -> bool:
    return bool(get_settings().groq_api_key) and not llm_down


def _chat(system: str, user: str) -> str | None:
    settings = get_settings()
    if not settings.groq_api_key:
        return None
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_groq import ChatGroq

        model = ChatGroq(api_key=settings.groq_api_key, model=settings.groq_model, temperature=0.2)
        resp = model.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        return str(resp.content or "").strip()
    except Exception:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_groq import ChatGroq

            model = ChatGroq(
                api_key=settings.groq_api_key,
                model=settings.groq_fallback_model,
                temperature=0.1,
            )
            resp = model.invoke([SystemMessage(content=system), HumanMessage(content=user)])
            return str(resp.content or "").strip()
        except Exception as exc:
            log.warning("groq unavailable: %s", exc)
            return None


def classify_unknown(rar: RevenueAtRisk, llm_down: bool) -> Diagnosis | None:
    if not groq_available(llm_down):
        return None
    text = _chat(
        "Classify a Razorpay payment failure. JSON only: "
        '{"class": "<one of: ' + CLASS_LIST + '>", "rationale": "max 3 sentences"}.',
        rar.model_dump_json(),
    )
    if not text:
        return None
    try:
        data = json.loads(text[text.find("{") : text.rfind("}") + 1])
        return Diagnosis(
            klass=DiagnosisClass(data["class"]),
            confidence="medium",
            source="groq",
            rationale=str(data.get("rationale") or "")[:500],
        )
    except Exception:
        return None


def write_rationale(rar: RevenueAtRisk, klass: DiagnosisClass, llm_down: bool) -> str | None:
    if not groq_available(llm_down):
        return None
    return _chat(
        "Razorpay revenue-recovery analyst. 3 sentences. No PII. No invented charges.",
        json.dumps(
            {
                "class": klass.value,
                "method": rar.method,
                "error_code": rar.error_code,
                "error_reason": rar.error_reason,
                "error_source": rar.error_source,
                "source_event": rar.source_event.value,
                "amount_paise": rar.amount_paise,
            }
        ),
    )


def compose_customer_copy(
    *,
    klass: str,
    action: str,
    amount_paise: int,
    locale: Locale,
    llm_down: bool,
) -> str | None:
    if not groq_available(llm_down):
        return None
    lang = "Hinglish (Hindi+English, Latin script)" if locale == Locale.HINGLISH else "clear Indian English"
    return _chat(
        "One short failed-payment customer message. No guilt, no threats. Include {{link}}. "
        f"Language: {lang}. Max 60 words.",
        f"class={klass} action={action} amount=₹{amount_paise / 100:.2f}",
    )


classify_unknown = classify_unknown
write_rationale = write_rationale
compose_customer_copy = compose_customer_copy
groq_available = groq_available
