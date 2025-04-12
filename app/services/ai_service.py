import json
import os
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import ValidationError
from openai import AsyncOpenAI
from dotenv import load_dotenv
from app.models.requests import CVAnalysisRequest, CVAnalysis

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set logging level to INFO
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

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
                                    "id": {"type": "string"},
                                    "company": {"type": "string"},
                                    "position": {"type": "string"},
                                    "startDate": {"type": "string"},
                                    "endDate": {"type": "string"},
                                    "current": {"type": "boolean"},
                                    "location": {"type": "string"},
                                    "description": {"type": "string"},
                                    "achievements": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                },
                                "required": ["id", "company", "position", "startDate", "endDate", "current", "location", "description", "achievements"]
                            }
                        },
                        "skills": {
                            "type": "array",
                            "items": {"type": "string"}  # Skills as a list of strings
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
        utc_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"Rewrite content process started at {utc_time} UTC")
        prompt = cls.generate_prompt(req, rules)  # Pass rules to generate_prompt
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
    def generate_prompt(req: CVAnalysisRequest, rules: dict) -> str:
        """
        Generate a prompt for the AI model based on the request and rules.
        """
        # Format skills
        skills_text = ", ".join([skill.name for skill in req.skills])

        # Format experiences
        experiences_text = ""
        for exp in req.experiences:
            # Use startDate, endDate, and current directly
            period_text = f"{exp.startDate} - {exp.endDate} (Current: {exp.current})"
            experiences_text += (
                f"{exp.position}\n{exp.company}\n{period_text}\n{exp.location}\n"
                f"Description: {exp.description}\n"
            )
            for achievement in exp.achievements:
                experiences_text += f"- {achievement}\n"
            experiences_text += "\n"

        # Format rules
        rules_text = "\n".join([f"- {key}: {value}" for key, value in rules.items()])

        # Construct the prompt
        prompt = (
            f"You are a Certified Professional Resume Writer, with over 20 years of experience in tailoring CVs "
            f"for job seekers in various industries.\n\n"
            f"JOB DESCRIPTION:\n{req.jobDescription}\n\n"
            f"CANDIDATE SKILLS:\n{skills_text}\n\n"
            f"EXISTING RESUME:\n{experiences_text}\n\n"
            f"INSTRUCTIONS:\n"
            f"Please enhance the EXISTING RESUME content to better align with the JOB DESCRIPTION. "
            f"Do not add new job titles, roles, or duties that do not exist in the original resume. "
            f"Your task is to improve the language, add relevant keywords, and adjust the format of the work experience, descriptions, and skills "
            f"to better reflect the job description, while keeping the original content intact.\n\n"
            f"RULES:\n{rules_text}\n\n"
            f"Use the provide_edited_cv function to return your enhanced resume in a structured format with sections for "
            f"experiences (with company name, job title, startDate,  endDate, current, location, descriptions, and achievements), skills, and a professionalSummary."
        )
        return prompt

    @staticmethod
    def transform_ai_response(ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform AI response to match our model structure"""
        transformed = {
            "experiences": ai_response.get("experiences", []),
            "skills": [skill["name"] for skill in ai_response.get("skills", [])],  # Extract skill names
            "professionalSummary": ai_response.get("professionalSummary", "Professional Summary Not Available")
        }
        return transformed
    
    @staticmethod
    def create_fallback_response(req: CVAnalysisRequest) -> Dict[str, Any]:
        """Create a fallback response when AI fails"""
        logger.warning("Using fallback response due to AI processing errors")
        return {
            "experiences": [exp.dict() for exp in req.experiences],
            "skills": [skill.name for skill in req.skills],  # Extract skill names
            "professionalSummary": "Fallback: Experienced professional with relevant skills."
        }