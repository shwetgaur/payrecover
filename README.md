# PayRecover

Diagnose failed payments. Recover the ones that should come back. Stop the ones that should not.

Razorpay AI Buildathon — **Track 03 · AI Revenue Recovery**.

Repo: https://github.com/shwetgaur/payrecover

Live demo (when deployed): dashboard on Vercel + API on Render.

## Why this exists

Razorpay already retries some failures on a fixed cadence. Merchants still leak revenue when the *wrong* retry fires (stolen card, revoked mandate) or when the *right* retry is too soon (insufficient funds) or never happens (UPI timeout, abandoned checkout).

PayRecover is a **control plane**: ingest Razorpay-shaped events, diagnose with a rule catalog, gate every action in code, execute one bounded recovery step, write an audit ledger.

## Honest metrics (gold batch of 50)

From `python backend/eval/run_eval.py` (no Groq required):

| Metric | Value |
|---|---|
| Classification vs gold | **50/50** |
| Action in gold allow-set | **50/50** |
| Policy violations | **0** |
| Valid recovery recommendations | **42** |
| Human escalate | **5** |
| Policy-stop (do not retry) | **3** |
| Simulated ₹ recovered | labeled in the console; methodology in `/eval` |

## Stack

- API: FastAPI + Pydantic + SQLAlchemy
- API: FastAPI + Pydantic + SQLAlchemy
- Agent: LangGraph (diagnose → policy → plan → compose → act → observe)
- LLM: Groq via LangChain (`ChatGroq`), with deterministic rule fallback
- UI: Next.js
- Data: 50 synthetic events in Razorpay webhook shape

## Run locally

```powershell
cd payrecover
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
copy .env.example .env
# optional: GROQ_API_KEY=...

# API
$env:PYTHONPATH="backend"
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

```powershell
cd web
npm install
$env:NEXT_PUBLIC_API_URL="http://127.0.0.1:8000"
npm run dev
```

Open http://localhost:3000 → **Run recovery on sample batch (50)**.

Eval:

```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python backend\eval\run_eval.py
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + LLM mode |
| POST | `/webhooks/razorpay` | `payment.failed` (HMAC if secret set) |
| POST | `/api/v1/runs` | Run sample batch |
| GET | `/api/v1/runs/{id}` | Run + cases + audit |
| GET | `/api/v1/cases/{id}` | Case drawer |
| GET | `/api/v1/metrics` | Latest KPIs |
| POST | `/api/v1/demo/faults` | `{ "llm": "down" }` |

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and the in-app `/architecture` page.

Pitch script: [docs/PITCH.md](docs/PITCH.md).

I also ship production RAG. This repo is the Track 03 product.

## Deploy (Vercel + Render + Groq)

PayRecover splits into a **Next.js console on Vercel** and a **FastAPI API on Render** with **Groq** for live rationale + customer copy (rules still run if Groq is down).

### 1. API on Render (Blueprint)

1. [Render dashboard](https://dashboard.render.com) → **New** → **Blueprint**
2. Connect repo `shwetgaur/payrecover` (branch `main`)
3. Render creates **payrecover-api** + **Postgres** from `render.yaml`
4. Set secret **`GROQ_API_KEY`** (from [console.groq.com](https://console.groq.com/keys))
5. After deploy, confirm: `GET https://payrecover-api.onrender.com/health` → `"llm": "live"`

Optional env overrides: `GROQ_MODEL`, `GROQ_FALLBACK_MODEL` (defaults in `render.yaml`).

### 2. Console on Vercel

1. [vercel.com/new](https://vercel.com/new) → import `shwetgaur/payrecover`
2. **Root Directory:** `web`
3. **Environment variable:**

| Key | Value |
|-----|--------|
| `NEXT_PUBLIC_API_URL` | `https://payrecover-api.onrender.com` |

4. Deploy → open the Vercel URL → **Run recovery on sample batch (50)**

CORS: the API auto-allows `*.vercel.app` when `CORS_ALLOW_VERCEL=true` (set in `render.yaml`).

**Memory (Render free 512 MB):** LangGraph + LangChain-Groq stay enabled. The API reuses a single `ChatGroq` client (not one per event), lazy-loads LangGraph on first run, and gc's during batch processing. If a 50-event batch still OOMs, upgrade the API to **Render Starter** ($7/mo, 2 GB) — no need to strip the agent stack.

### 3. Keep-alive (optional)

`.github/workflows/render-keep-alive.yml` pings `/health` every 14 minutes so the free Render API stays warm (public repo = unlimited Actions).

### Local dev env

```powershell
# API — backend/
GROQ_API_KEY=gsk_...

# Web — web/
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```
