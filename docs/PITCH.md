# 5-minute pitch — PayRecover

**One-liner:** Diagnose failed payments. Recover the ones that should come back. Stop the ones that should not.

**Track:** 03 — AI Revenue Recovery  
**Apply:** razorpay.com/buildathon

## First 60 seconds (live)

1. Open the live dashboard.
2. Click **Run recovery on sample batch (50)**.
3. KPIs tick: ₹ at risk, simulated ₹ recovered, **42 valid recs / 5 escalate / 3 policy-stop**.
4. Open a UPI timeout case — diagnosis, policy pass, retry after 15m, audit lines.
5. Toggle **LLM DOWN**. Same class of case still recovers via rules.
6. Open a do-not-retry case. The agent **stops**. That is the point.

## Remaining 4 minutes

- Razorpay error model (`error_reason` / `error_source` / `method`), not a generic classifier.
- Policy is code. Groq writes rationale and copy. Groq cannot authorize a retry the gate forbids.
- Honest metrics: 50/50 class match, 50/50 action in allow-set, 0 violations. Simulated recovery ~45% on this gold set — not 100%.
- SHL / Test Executor are off this page. One line in README: I also ship production RAG.

## What we are not claiming

- We do not replace Razorpay Smart Retry.
- We do not send real WhatsApp in week 1.
- We do not invent captured money. The counter is labeled simulated.

## Ask

Track 03 internship. This is the intern-shaped product: diagnosis, a hard gate, an audit trail, and one graceful failure.
