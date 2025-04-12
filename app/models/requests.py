from pydantic import BaseModel
from typing import List


class Skill(BaseModel):
    id: str
    name: str
    level: str


class Experiences(BaseModel):
    id: str
    company: str
    position: str
    startDate: str  # Start date of the experience
    endDate: str  # End date of the experience
    current: bool  # Whether the position is current
    location: str
    description: str
    achievements: List[str]


class CVAnalysisRequest(BaseModel):
    skills: List[Skill]
    jobDescription: str
    experiences: List[Experiences]  # Changed to match your payload structure


class CVAnalysis(BaseModel):
    experiences: List[Experiences]  # Updated to match the structure
    skills: List[str]
    professionalSummary: str