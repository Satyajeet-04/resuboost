from pydantic import BaseModel, Field
from typing import Literal, Optional

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
    context: str = Field("", max_length=50000)

class RewriteResponse(BaseModel):
    original: list[str]
    rewritten: list[str]
    explanation: str

class FullRewriteRequest(BaseModel):
    resume: str = Field(..., max_length=50000)
    gaps: list[str] = Field(..., description="List of skills to address")
    job_description: str = Field(..., max_length=50000)

class FullRewriteResponse(BaseModel):
    full_resume: str = Field(..., description="Complete rewritten resume text")
    changes_summary: str = Field("", description="What was changed and why")

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

# --- Cover Letter ---
class CoverLetterRequest(BaseModel):
    resume: str = Field(..., max_length=50000)
    job_description: str = Field(..., max_length=50000)

class CoverLetterResponse(BaseModel):
    cover_letter: str
    subject_line: str = ""
    key_points: list[str] = []

# --- Keywords ---
class KeywordItem(BaseModel):
    keyword: str
    in_resume: bool
    importance: Literal["high", "medium", "low"]
    category: str = ""
    suggestion: str = ""

class KeywordStats(BaseModel):
    total_keywords: int
    matched: int
    missing: int
    coverage_pct: float

class KeywordRequest(BaseModel):
    resume: str = Field(..., max_length=50000)
    job_description: str = Field(..., max_length=50000)

class KeywordResponse(BaseModel):
    keywords: list[KeywordItem]
    stats: KeywordStats
    top_missing: list[str] = []
    recommendation: str = ""

# --- Resume Score ---
class ScoreItem(BaseModel):
    category: str
    score: int = Field(..., ge=0, le=100)
    max_score: int = 100
    reason: str
    tip: str = ""

class ScoreRequest(BaseModel):
    resume: str = Field(..., max_length=50000)
    job_description: str = Field(..., max_length=50000)

class ScoreResponse(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    scores: list[ScoreItem]
    strengths: list[str] = []
    weaknesses: list[str] = []
    priority_fixes: list[str] = []

# --- Interview Questions ---
class QuestionItem(BaseModel):
    question: str
    category: str = ""
    difficulty: str = ""
    why_asked: str = ""
    preparation_tip: str = ""

class InterviewQuestionsRequest(BaseModel):
    resume: str = Field(..., max_length=50000)
    job_description: str = Field(..., max_length=50000)
    gaps: list[str] = []

class InterviewQuestionsResponse(BaseModel):
    questions: list[QuestionItem]
    total_questions: int = 0
    categories_covered: list[str] = []

# --- ATS Breakdown ---
class AtsParseability(BaseModel):
    score: int = Field(..., ge=0, le=100)
    issues: list[str] = []

class AtsKeywordMatch(BaseModel):
    score: int = Field(..., ge=0, le=100)
    matched: list[str] = []
    missing: list[str] = []

class AtsSectionCompat(BaseModel):
    clean: bool = True
    issues: list[str] = []
    warning: str = ""

class AtsBreakdownResult(BaseModel):
    platform: str
    overall_score: int = Field(..., ge=0, le=100)
    parseability: AtsParseability
    keyword_match: AtsKeywordMatch
    section_compatibility: AtsSectionCompat
    specific_feedback: str = ""
    action_items: list[str] = []

class AtsBreakdownRequest(BaseModel):
    resume: str = Field(..., max_length=50000)
    job_description: str = Field(..., max_length=50000)
    platform: str = "greenhouse"

class AtsBreakdownResponse(BaseModel):
    result: AtsBreakdownResult

# --- Shortlist Mode ---
class ShortlistRequest(BaseModel):
    resume: str = Field(..., max_length=50000)
    job_description: str = Field(..., max_length=50000)
    aggressive: bool = Field(False, description="Maximum tailoring intensity")

class ShortlistIteration(BaseModel):
    iteration: int
    score: int = Field(..., ge=0, le=100)
    remaining_weaknesses: int = 0

class ShortlistResponse(BaseModel):
    resume: str
    original_resume: str = ""
    final_score: int = Field(..., ge=0, le=100)
    shortlist_verified: bool
    iterations: list[ShortlistIteration]
    changes_summary: str = ""
