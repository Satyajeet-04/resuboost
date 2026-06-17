from pydantic import BaseModel, Field
from typing import Literal

class AnalyzeRequest(BaseModel):
    resume: str = Field(..., max_length=50000, description="Full resume text")
    job_description: str = Field(..., max_length=50000, description="Job description text")

class GapItem(BaseModel):
    skill: str = Field(..., description="Missing skill or qualification")
    importance: Literal["high", "medium", "low"]
    reason: str = Field(..., description="Why this matters for this specific role")

class AnalyzeResponse(BaseModel):
    gaps: list[GapItem]
    match_score: int = Field(..., ge=0, le=100, description="Overall resume-JD fit percentage")

class RewriteRequest(BaseModel):
    resume: str = Field(..., max_length=50000)
    skill: str = Field(..., max_length=500)
    context: str = Field("", max_length=2000)

class RewriteResponse(BaseModel):
    original: list[str]
    rewritten: list[str]
    explanation: str

class SimulateRequest(BaseModel):
    resume: str = Field(..., max_length=50000)
    role: str = Field(..., max_length=500)

class SimQuery(BaseModel):
    query: str
    match: bool
    why: str

class SimulateResponse(BaseModel):
    queries: list[SimQuery]
    match_rate: int = Field(..., ge=0, le=100)
