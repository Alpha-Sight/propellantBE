import json
import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ValidationError
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageToolCall
from dotenv import load_dotenv
from app.models.requests import CVAnalysisRequest, CVAnalysis, WorkExperience

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
                        "work_experience": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "company_name": {"type": "string"},
                                    "job_title": {"type": "string"},
                                    "duration": {"type": "string"},
                                    "duties": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                },
                                "required": ["company_name", "job_title", "duration", "duties"]
                            }
                        },
                        "skills": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "professional_summary": {"type": "string"}
                    },
                    "required": ["work_experience", "skills", "professional_summary"]
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
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                tools=tools,
                tool_choice="auto"
            )
            
            # Process tool calls from the response
            tool_calls = response.choices[0].message.tool_calls
            if not tool_calls:
                raise ValueError("No tool calls received from AI model")
                
            # Process the first tool call (should be provide_edited_cv)
            tool_call = tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            
            try:
                # Parse the function arguments with Pydantic for validation
                parsed_response = CVAnalysis(**function_args)
                return parsed_response
            except ValidationError as e:
                raise ValueError(f"Failed to parse AI response: {str(e)}")
                
        except Exception as e:
            print(f"Error communicating with UnifyAI: {str(e)}")
            raise e
    
    @staticmethod
    def generate_prompt(req: CVAnalysisRequest, rules: dict) -> str:
        """Generate a prompt for the AI model based on the request and rules"""
        rules_text = "\n".join([f"- {key}: {value}" for key, value in rules.items()])
        prompt = (
            f"You are a Certified Professional Resume Writer, with over 20 years of experience in tailoring CVs "
            f"for job seekers in various industries. \n\n"
            f"JOB DESCRIPTION:\n{req.job_description}\n\n"
            f"CANDIDATE SKILLS:\n{req.skills}\n\n"
            f"EXISTING RESUME:\n{req.cv_text}\n\n"
            f"INSTRUCTIONS:\n"
            f"Please enhance the EXISTING RESUME content to better align with the JOB DESCRIPTION. "
            f"Do not add new job titles, roles, or duties that do not exist in the original resume. "
            f"Your task is to improve the language, add relevant keywords, and adjust the format of the work experience and skills "
            f"to better reflect the job description, while keeping the original content intact.\n\n"
            f"RULES:\n{rules_text}\n\n"
            f"Use the provide_edited_cv function to return your enhanced resume in a structured format with sections for "
            f"work experience (with company name, job title, duration, and duties), skills, and a professional summary."
        )
        return prompt