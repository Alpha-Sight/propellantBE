import json
import os
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ValidationError
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageToolCall
from dotenv import load_dotenv
from app.models.requests import CVAnalysisRequest, CVAnalysis

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Load Unify AI specific credentials
UNIFY_URL = os.getenv("UNIFY_URL")
UNIFY_API_KEY = os.getenv("UNIFY_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")

# Validate environment variables
if not UNIFY_URL or not UNIFY_API_KEY or not MODEL_NAME:
    raise ValueError("Missing required environment variables for UnifyAI integration")

# Initialize the OpenAI client
client = AsyncOpenAI(
    base_url=UNIFY_URL,
    api_key=UNIFY_API_KEY
)

class AIService:
    @staticmethod
    def edit_cv():
        """Define the edit_cv tool for the AI model"""
        return {
            "type": "function",
            "function": {
                "name": "provide_edited_cv",
                "description": "Enhance a CV/resume to better match a job description",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "experiences": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "company": {"type": "string"},
                                    "jobTitle": {"type": "string"},
                                    "period": {
                                        "type": "object",
                                        "properties": {
                                            "start": {"type": "string"},
                                            "end": {"type": "string"}
                                        },
                                        "required": ["start", "end"]
                                    },
                                    "location": {"type": "string"},
                                    "duties": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                },
                                "required": ["jobTitle", "company", "period", "location", "duties"]
                            }
                        },
                        "skills": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "professionalSummary": {"type": "string"}
                    },
                    "required": ["experiences", "skills", "professionalSummary"]
                }
            }
        }

    @classmethod
    async def rewrite_content(cls, req: CVAnalysisRequest, rules: dict) -> dict:
        """
        Send request to UnifyAI and get a structured response
        """
        prompt = cls.generate_prompt(req, rules)
        tools = [cls.edit_cv()]
        
        try:
            logger.info("Sending request to UnifyAI...")
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                tools=tools,
                tool_choice="auto"
            )
            
            # Process tool calls from the response
            tool_calls = response.choices[0].message.tool_calls
            if not tool_calls:
                logger.warning("No tool calls received from AI model")
                return cls.create_fallback_response(req)
                
            # Process the first tool call (should be provide_edited_cv)
            tool_call = tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            
            # Log the raw response for debugging
            logger.debug(f"AI response: {json.dumps(function_args)}")
            
            # Try different approaches to handle the response
            try:
                # Approach 1: Direct parsing with Pydantic
                try:
                    parsed_response = CVAnalysis(**function_args)
                    logger.info("Successfully parsed AI response directly")
                    return parsed_response.model_dump()
                except ValidationError as e1:
                    logger.warning(f"Direct parsing failed: {str(e1)}")
                    
                # Approach 2: Transform the response and try again
                transformed_data = cls.transform_ai_response(function_args)
                try:
                    parsed_response = CVAnalysis(**transformed_data)
                    logger.info("Successfully parsed transformed AI response")
                    return parsed_response.model_dump()
                except ValidationError as e2:
                    logger.warning(f"Transformed parsing failed: {str(e2)}")
                    
                # Approach 3: Manually construct a valid response
                logger.warning("Both parsing approaches failed, constructing manual response")
                return cls.create_manual_response(function_args, req)
                
            except Exception as e:
                logger.error(f"Failed to process AI response: {str(e)}")
                return cls.create_fallback_response(req)
                
        except Exception as e:
            logger.error(f"Error communicating with UnifyAI: {str(e)}")
            return cls.create_fallback_response(req)
    
    @staticmethod
    def transform_ai_response(ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform AI response to match our model structure"""
        transformed = {}
        
        # Check both field names correctly
        if "experiences" in ai_response:
            transformed["experiences"] = ai_response["experiences"]
        elif "work_experience" in ai_response:  # Changed from "experiences" to "work_experience"
            transformed["experiences"] = ai_response["work_experience"]
        else:
            # Default empty experiences array
            transformed["experiences"] = []
        
        # Copy skills directly
        if "skills" in ai_response:
            transformed["skills"] = ai_response["skills"]
        else:
            transformed["skills"] = []
            
        # Copy professionalSummary directly
        if "professionalSummary" in ai_response:
            transformed["professionalSummary"] = ai_response["professionalSummary"]
        else:
            transformed["professionalSummary"] = "Professional Summary Not Available"
            
        return transformed
    
    @staticmethod
    def create_manual_response(ai_response: Dict[str, Any], req: CVAnalysisRequest) -> Dict[str, Any]:
        """Manually construct a valid response structure from AI data"""
        response = {}
        
        # Check both field names correctly
        if "experiences" in ai_response:
            response["experiences"] = ai_response["experiences"]
        elif "work_experience" in ai_response:  # Changed from "experiences" to "work_experience"
            response["experiences"] = ai_response["work_experience"]
        else:
            # Create default experiences from CV text
            lines = req.cv_text.split("\n")
            company = "Unknown Company"
            job_title = "Unknown Role"
            period = "Unknown Period"
            location = "Unknown Location"
            duties = ["Responsibility extracted from CV"]
            
            for line in lines:
                if "Developer" in line or "Engineer" in line:
                    job_title = line.strip()
                elif "20" in line and "-" in line:
                    period = line.strip()
                
            response["experiences"] = [
                {
                    "company": company,
                    "jobTitle": job_title,
                    "period": period,
                    "location": location,
                    "duties": duties
                }
            ]
        
        # Handle skills
        if "skills" in ai_response:
            response["skills"] = ai_response["skills"]
        else:
            # Use the skills from the request
            response["skills"] = req.skills
            
        # Handle professional summary
        if "professionalSummary" in ai_response:
            response["professionalSummary"] = ai_response["professionalSummary"]
        else:
            # Extract first paragraph from CV as summary
            summary = "Professional with relevant experience in the field."
            for line in req.cv_text.split("\n\n"):
                if "SUMMARY" in line.upper() or "PROFILE" in line.upper():
                    summary = line.replace("PROFESSIONAL SUMMARY", "").replace("SUMMARY", "").strip()
                    break
            response["professionalSummary"] = summary
            
        return response
    
    @staticmethod
    def create_fallback_response(req: CVAnalysisRequest) -> Dict[str, Any]:
        """Create a fallback response when AI fails"""
        logger.warning("Using fallback response due to AI processing errors")
        
        # Extract basic info from the CV for the fallback
        lines = req.cv_text.split("\n")
        company = "Tech Company"
        job_title = "Developer"
        period = "2020 - Present"
        location = "Remote"
        
        for line in lines:
            if "Developer" in line or "Engineer" in line:
                job_title = line.strip()
            elif "20" in line and "-" in line:
                period = line.strip()
            elif "Inc" in line or "LLC" in line or "Ltd" in line:
                company = line.strip()
        
        return {
            "experiences": [
                {
                    "company": company,
                    "jobTitle": job_title,
                    "period": period,
                    "location": location,
                    "duties": [
                        "Developed and maintained software applications",
                        "Collaborated with team members on projects",
                        "Implemented features based on requirements",
                        "Ensured code quality through testing"
                    ]
                }
            ],
            "skills": req.skills,
            "professionalSummary": "Experienced professional with skills in " + ", ".join(req.skills[:3]) + " and related technologies."
        }
    
    @staticmethod
    def generate_prompt(req: CVAnalysisRequest, rules: dict) -> str:
        """Generate a prompt for the AI model based on the request and rules"""
        rules_text = "\n".join([f"- {key}: {value}" for key, value in rules.items()])
        
        # Access fields using correct attribute names
        jobDescription = req.jobDescription
        skills_text = ", ".join(req.skills) if isinstance(req.skills, list) else req.skills
        cv_text = req.cv_text
        
        prompt = (
            f"You are a Certified Professional Resume Writer, with over 20 years of experience in tailoring CVs "
            f"for job seekers in various industries. \n\n"
            f"JOB DESCRIPTION:\n{jobDescription}\n\n"
            f"CANDIDATE SKILLS:\n{skills_text}\n\n"
            f"EXISTING RESUME:\n{cv_text}\n\n"
            f"INSTRUCTIONS:\n"
            f"Please enhance the EXISTING RESUME content to better align with the JOB DESCRIPTION. "
            f"Do not add new job titles, roles, or duties that do not exist in the original resume. "
            f"Your task is to improve the language, add relevant keywords, and adjust the format of the work experience and skills "
            f"to better reflect the job description, while keeping the original content intact.\n\n"
            f"RULES:\n{rules_text}\n\n"
            f"Use the provide_edited_cv function to return your enhanced resume in a structured format with sections for "
            f"experiences (with company name, job title, period, location, and duties), skills, and a professionalSummary."
        )
        return prompt