from pydantic import BaseModel
from typing import List


class Period(BaseModel):
    start: str
    end: str

class CVAnalysisRequest(BaseModel):
    skills: List[str] = []
    jobDescription: str
    cv_text: str

class experiences(BaseModel):
    jobTitle: str
    company: str
    period: Period
    location: str
    duties: List[str]

class CVAnalysis(BaseModel):
    experiences: List[experiences]
    skills: List[str]
    professionalSummary: str