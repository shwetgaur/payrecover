# PayRecover architecture

PayRecover is a **merchant recovery control plane** for Razorpay Track 03. It sits on top of payment events. It does not replace Smart Retry. It decides *whether* to retry, *when*, and *when to stop*.

## Flow

```
webhook / CSV / sample batch
        │
        ▼
 HMAC + idempotency (event.id)
        │
        ▼
 Normalize → RevenueAtRisk
        │
        ▼
 LangGraph
   diagnose  (rules first, Groq writes rationale)
        │
   policy gate  (code, not a prompt)
        │
   plan  (one bounded action + stop condition)
        │
   compose  (English / Hinglish)
        │
   act  (simulated adapters in MVP)
        │
   observe
        │
        ▼
 Append-only audit ledger → merchant console
```

## Why this is not a chatbot

Razorpay already has T+3 subscription retries and generic failure emails. PayRecover adds a **diagnosing decision layer**:

- Uses native fields: `error_code`, `error_source`, `error_step`, `error_reason`, `method`
- Refuses recovery on stolen/fraud/blocked instruments and revoked mandates
- Times insufficient-funds differently from UPI timeouts
- Executes **one** bounded action with a stop condition
- Writes a compliance-readable ledger
- Survives Groq being down (rule catalog still classifies and acts)

## Policy (hard, in code)

- Max 2 recovery actions per payment
- Max 2 customer touches / 7 days
- Quiet hours 21:00–09:00 IST → queue, do not send
- WhatsApp only if `consent.whatsapp`
- Never retry `do_not_retry`, `mandate_revoked`, `already_resolved`
- Amounts stay in paise; PII in the ledger is hashed

The LLM never bypasses this gate.

## Honest money

Adapters are **simulated** with a published probability table (`backend/data/error_catalog.yaml`). The console labels recovered rupees as simulated. Eval methodology lives in `backend/eval/run_eval.py`.

Gold batch (50 events, frozen clock 2026-08-22 14:30 IST):

| Bucket | Count |
|---|---|
| Valid recovery recommendation | 42 |
| Human escalate | 5 |
| Policy-stop | 3 |
| Policy violations | 0 |

## Graceful failure

Toggle **LLM DOWN** in the console. Diagnose still runs from the catalog. WhatsApp timeout queues the action, marks the case `degraded`, and continues.

## Stack

- FastAPI + Pydantic v2 + SQLAlchemy (SQLite locally, Postgres on Render)
- LangGraph (diagnose → policy → plan → compose → act → observe)
- Groq `llama-3.3-70b-versatile` with `llama-3.1-8b-instant` fallback
- Next.js console (Vercel)
