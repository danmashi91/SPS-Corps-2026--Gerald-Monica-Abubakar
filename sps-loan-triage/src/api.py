import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from orchestrator import run_pipeline

app = FastAPI(title="Loan Triage Decision-Support Tool")

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

class LoanApplicationRequest(BaseModel):
    credit_score: int
    monthly_income: float
    debt_to_income_ratio: float
    recent_delinquencies: int
    loan_amount_requested: float

@app.get("/")
def serve_ui():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.post("/api/triage")
def run_triage(request: LoanApplicationRequest):
    application_input = request.model_dump()
    result = run_pipeline(application_input)
    return result

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Loan Triage Decision-Support Tool"}
