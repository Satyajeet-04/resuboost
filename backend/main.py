from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from models.schemas import *
from services.gap_analyzer import GapAnalyzer
from services.rewriter import Rewriter
from services.simulator import Simulator
from services.full_rewriter import FullRewriter
from services.cover_letter import CoverLetterGenerator
from services.keywords import KeywordAnalyzer
from services.resume_scorer import ResumeScorer
from services.interview_questions import InterviewQuestionGenerator
from services.ats_breakdown import ATSBreakdown
from utils.sanitizer import sanitize
from config import settings
import json
import traceback

app = FastAPI(title="ResuBoost API", version="1.0.0")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    msg = str(exc)
    status = 500
    lower = msg.lower()
    if "rate limit" in lower or "quota" in lower or "resource exhausted" in lower or "429" in msg:
        status = 429
    return JSONResponse(status_code=status, content={"detail": msg})

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

from services.groq_client import MODEL_ROUTES
import os
import requests

@app.get("/debug/groq")
def debug_groq():
    results = {}
    # Test 1: Basic network to groq.com
    try:
        resp = requests.get("https://api.groq.com/openai/v1/models", timeout=10)
        results["models_connect"] = {"status": resp.status_code, "body": resp.text[:200]}
    except Exception as e:
        results["models_connect"] = {"error": str(e), "trace": traceback.format_exc()[-500:]}
    
    # Test 2: Try a simple chat completion
    api_key = os.getenv("GROQ_API_KEY", "")
    if api_key:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "ResuBoost/1.0",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": "say hi json {\"word\": \"test\"}"}],
                    "temperature": 0.2,
                    "max_tokens": 50,
                    "response_format": {"type": "json_object"},
                },
                timeout=15,
            )
            results["chat_test"] = {
                "status": resp.status_code,
                "body": resp.text[:300],
                "headers": dict(resp.headers),
            }
        except Exception as e:
            results["chat_test"] = {"error": str(e)[:300], "trace": traceback.format_exc()[-300:]}
    
    results["groq_key_set"] = bool(api_key)
    results["groq_key_len"] = len(api_key)
    results["groq_key_prefix"] = api_key[:7] if api_key else ""
    return results

@app.get("/health")
def health():
    return {
        "status": "ok",
        "provider": "groq",
        "models": MODEL_ROUTES,
        "groq_key_set": bool(os.getenv("GROQ_API_KEY", "")),
    }

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

@app.post("/cover_letter", response_model=CoverLetterResponse)
async def cover_letter(req: CoverLetterRequest):
    safe_resume = sanitize(req.resume) if settings.strip_pii else req.resume
    safe_jd = sanitize(req.job_description) if settings.strip_pii else req.job_description
    if len(safe_resume) > settings.max_input_length:
        safe_resume = safe_resume[:settings.max_input_length]
    if len(safe_jd) > settings.max_input_length:
        safe_jd = safe_jd[:settings.max_input_length]
    try:
        return CoverLetterGenerator().generate(safe_resume, safe_jd)
    except json.JSONDecodeError:
        raise HTTPException(502, "AI returned invalid response format")

@app.post("/keywords", response_model=KeywordResponse)
async def keywords(req: KeywordRequest):
    safe_resume = sanitize(req.resume) if settings.strip_pii else req.resume
    safe_jd = sanitize(req.job_description) if settings.strip_pii else req.job_description
    if len(safe_resume) > settings.max_input_length:
        safe_resume = safe_resume[:settings.max_input_length]
    if len(safe_jd) > settings.max_input_length:
        safe_jd = safe_jd[:settings.max_input_length]
    try:
        return KeywordAnalyzer().analyze(safe_resume, safe_jd)
    except json.JSONDecodeError:
        raise HTTPException(502, "AI returned invalid response format")

@app.post("/score", response_model=ScoreResponse)
async def score(req: ScoreRequest):
    safe_resume = sanitize(req.resume) if settings.strip_pii else req.resume
    safe_jd = sanitize(req.job_description) if settings.strip_pii else req.job_description
    if len(safe_resume) > settings.max_input_length:
        safe_resume = safe_resume[:settings.max_input_length]
    if len(safe_jd) > settings.max_input_length:
        safe_jd = safe_jd[:settings.max_input_length]
    try:
        return ResumeScorer().score(safe_resume, safe_jd)
    except json.JSONDecodeError:
        raise HTTPException(502, "AI returned invalid response format")

@app.post("/interview_questions", response_model=InterviewQuestionsResponse)
async def interview_questions(req: InterviewQuestionsRequest):
    safe_resume = sanitize(req.resume) if settings.strip_pii else req.resume
    safe_jd = sanitize(req.job_description) if settings.strip_pii else req.job_description
    if len(safe_resume) > settings.max_input_length:
        safe_resume = safe_resume[:settings.max_input_length]
    if len(safe_jd) > settings.max_input_length:
        safe_jd = safe_jd[:settings.max_input_length]
    try:
        return InterviewQuestionGenerator().generate(safe_resume, safe_jd, req.gaps)
    except json.JSONDecodeError:
        raise HTTPException(502, "AI returned invalid response format")

@app.post("/ats_breakdown", response_model=AtsBreakdownResponse)
async def ats_breakdown(req: AtsBreakdownRequest):
    safe_resume = sanitize(req.resume) if settings.strip_pii else req.resume
    safe_jd = sanitize(req.job_description) if settings.strip_pii else req.job_description
    if len(safe_resume) > settings.max_input_length:
        safe_resume = safe_resume[:settings.max_input_length]
    if len(safe_jd) > settings.max_input_length:
        safe_jd = safe_jd[:settings.max_input_length]
    try:
        result = ATSBreakdown(platform=req.platform).analyze(safe_resume, safe_jd)
        return {"result": result}
    except json.JSONDecodeError:
        raise HTTPException(502, "AI returned invalid response format")
