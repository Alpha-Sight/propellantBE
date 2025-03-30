from pydantic import BaseModel
from typing import List

class CVAnalysisRequest(BaseModel):
    skills: str = ""
    job_description: str
    cv_text: str

class WorkExperience(BaseModel):
    company_name: str
    job_title: str
    duration: str
    duties: List[str]

class CVAnalysis(BaseModel):
    work_experience: List[WorkExperience]
    skills: List[str]
    professional_summary: str