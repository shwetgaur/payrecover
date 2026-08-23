from __future__ import annotations

import json

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session, init_db
from app.faults import get_faults, set_faults
from app.ingest import load_sample_batch
from app.schemas import FaultRequest, FaultState, RunRequest
from app.services import get_case, get_run, ingest_webhook, latest_metrics, run_batch

settings = get_settings()
init_db()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_origin_regex=r"https://.*\.vercel\.app" if settings.cors_allow_vercel else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health(db: Session = Depends(get_session)) -> dict:
    faults = get_faults(db)
    return {
        "ok": True,
        "app": settings.app_name,
        "llm": "fallback" if (faults.llm == "down" or not settings.groq_api_key) else "live",
        "faults": faults.model_dump(),
    }


@app.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    db: Session = Depends(get_session),
):
    body = await request.body()
    try:
        return ingest_webhook(db, body, x_razorpay_signature)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/events/batch")
async def upload_batch(
    req: RunRequest | None = None,
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_session),
):
    request = req or RunRequest()
    events = None
    if file:
        events = json.loads((await file.read()).decode("utf-8"))
        if isinstance(events, dict):
            events = events.get("events") or events.get("items") or [events]
    return run_batch(db, request, events)


@app.post("/api/v1/runs")
def create_run(req: RunRequest | None = None, db: Session = Depends(get_session)):
    return run_batch(db, req or RunRequest(), load_sample_batch())


@app.get("/api/v1/runs/{run_id}")
def read_run(run_id: str, db: Session = Depends(get_session)):
    out = get_run(db, run_id)
    if not out:
        raise HTTPException(status_code=404, detail="run not found")
    return out


@app.get("/api/v1/cases/{case_id}")
def read_case(case_id: str, db: Session = Depends(get_session)):
    out = get_case(db, case_id)
    if not out:
        raise HTTPException(status_code=404, detail="case not found")
    return out


@app.get("/api/v1/metrics")
def metrics(db: Session = Depends(get_session)):
    return latest_metrics(db)


@app.get("/api/v1/demo/faults")
def read_faults(db: Session = Depends(get_session)) -> FaultState:
    return get_faults(db)


@app.post("/api/v1/demo/faults")
def write_faults(req: FaultRequest, db: Session = Depends(get_session)) -> FaultState:
    return set_faults(db, llm=req.llm, whatsapp=req.whatsapp)
