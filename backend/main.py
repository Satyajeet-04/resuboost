from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models.schemas import *
from services.gap_analyzer import GapAnalyzer
from services.rewriter import Rewriter
from services.simulator import Simulator
from services.full_rewriter import FullRewriter
from utils.sanitizer import sanitize
from config import settings
import json

app = FastAPI(title="ResuBoost API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://satyajeet-04.github.io",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
    ],
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)

@app.get("/health")
def health():
    return {"status": "ok", "model": settings.gemini_model}

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    safe_resume = sanitize(req.resume) if settings.strip_pii else req.resume
    safe_jd = sanitize(req.job_description) if settings.strip_pii else req.job_description

    if len(safe_resume) > settings.max_input_length:
        safe_resume = safe_resume[:settings.max_input_length]
    if len(safe_jd) > settings.max_input_length:
        safe_jd = safe_jd[:settings.max_input_length]

    try:
        result = GapAnalyzer().analyze(safe_resume, safe_jd)
        return result
    except json.JSONDecodeError:
        raise HTTPException(502, "AI returned invalid response format")
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")

@app.post("/rewrite", response_model=RewriteResponse)
async def rewrite(req: RewriteRequest):
    safe_resume = sanitize(req.resume) if settings.strip_pii else req.resume
    if len(safe_resume) > settings.max_input_length:
        safe_resume = safe_resume[:settings.max_input_length]

    try:
        result = Rewriter().rewrite(safe_resume, req.skill, req.context)
        return result
    except json.JSONDecodeError:
        raise HTTPException(502, "AI returned invalid response format")
    except Exception as e:
        raise HTTPException(500, f"Rewrite failed: {str(e)}")

@app.post("/full_rewrite", response_model=FullRewriteResponse)
async def full_rewrite(req: FullRewriteRequest):
    safe_resume = sanitize(req.resume) if settings.strip_pii else req.resume
    if len(safe_resume) > settings.max_input_length:
        safe_resume = safe_resume[:settings.max_input_length]

    try:
        result = FullRewriter().full_rewrite(safe_resume, req.gaps, req.job_description)
        return result
    except json.JSONDecodeError:
        raise HTTPException(502, "AI returned invalid response format")
    except Exception as e:
        raise HTTPException(500, f"Full rewrite failed: {str(e)}")

@app.post("/simulate", response_model=SimulateResponse)
async def simulate(req: SimulateRequest):
    safe_resume = sanitize(req.resume) if settings.strip_pii else req.resume
    if len(safe_resume) > settings.max_input_length:
        safe_resume = safe_resume[:settings.max_input_length]

    try:
        result = Simulator().simulate(safe_resume, req.role)
        return result
    except json.JSONDecodeError:
        raise HTTPException(502, "AI returned invalid response format")
    except Exception as e:
        raise HTTPException(500, f"Simulation failed: {str(e)}")
