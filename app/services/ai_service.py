import json
import os
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import ValidationError
from openai import AsyncOpenAI
from dotenv import load_dotenv
from app.models.requests import CVAnalysisRequest, CVAnalysis, Skill, Experiences

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
                        "professionalSummary": {"type": "string"}
                    },
                    "required": ["experiences", "professionalSummary"]
                }
            }
        }

    @classmethod
    async def rewrite_content(cls, req: CVAnalysisRequest, rules: dict) -> dict:
        """
        Send request to UnifyAI and get a structured response
        """
        utc_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        user_login = "praiseunite"
        logger.info(f"Rewrite content process started at {utc_time} UTC for user: {user_login}")
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
                logger.warning(f"No tool calls received from AI model at {utc_time} UTC for user: {user_login}")
                return cls.create_fallback_response(req)
                
            # Process the first tool call (should be provide_edited_cv)
            tool_call = tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            
            # Log the raw response for debugging
            logger.debug(f"AI response: {json.dumps(function_args)}")
            
            # Process the AI's experiences
            ai_experiences = function_args.get("experiences", [])
            
            # Fix any issues with IDs and achievements in experiences
            fixed_experiences = cls.process_experiences(ai_experiences, req.experiences)
            
            # Create response with enhanced experiences and original skills
            data = {
                "experiences": fixed_experiences,
                "skills": [skill.model_dump() for skill in req.skills],
                "professionalSummary": function_args.get("professionalSummary", "")
            }
            
            # Create a CVAnalysis object and validate it
            try:
                # First convert skills back to Skill objects
                skills_objects = [Skill(**skill) for skill in data["skills"]]
                
                # Create experiences objects
                experience_objects = []
                for exp in data["experiences"]:
                    experience_objects.append(Experiences(**exp))
                
                # Create and validate the final response
                response_model = CVAnalysis(
                    experiences=experience_objects,
                    skills=skills_objects,
                    professionalSummary=data["professionalSummary"]
                )
                
                curr_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"Successfully enhanced CV at {curr_time} UTC for user: {user_login}")
                
                return response_model.model_dump()
                
            except ValidationError as e:
                logger.error(f"Validation error: {str(e)}")
                return cls.create_fallback_response(req)
                
        except Exception as e:
            err_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            logger.error(f"Error communicating with UnifyAI: {str(e)} at {err_time} UTC for user: {user_login}")
            return cls.create_fallback_response(req)
    
    @staticmethod
    def process_experiences(ai_experiences, original_experiences):
        """Process and fix experiences from AI"""
        fixed_experiences = []
        original_exp_map = {exp.id: exp for exp in original_experiences}
        
        # Process each experience from AI
        for ai_exp in ai_experiences:
            # Match with original experience by company and position
            for orig_id, orig_exp in original_exp_map.items():
                if (ai_exp.get("company") == orig_exp.company and 
                    ai_exp.get("position") == orig_exp.position):
                    
                    # Set the correct ID
                    ai_exp["id"] = orig_id
                    
                    # Ensure achievements exist
                    if not ai_exp.get("achievements") or len(ai_exp.get("achievements", [])) == 0:
                        ai_exp["achievements"] = [ach for ach in orig_exp.achievements]
                        
                    break
            
            fixed_experiences.append(ai_exp)
            
        return fixed_experiences
    
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
            period_text = f"{exp.startDate} - {exp.endDate} (Current: {exp.current})"
            experiences_text += (
                f"ID: {exp.id}\n{exp.position}\n{exp.company}\n{period_text}\n{exp.location}\n"
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
            f"Please enhance ONLY the work experience descriptions and achievements to better align with the JOB DESCRIPTION. "
            f"Keep the exact same structure including IDs, company names, position titles, dates, and locations.\n\n"
            f"VERY IMPORTANT:\n"
            f"1. The ID field must be preserved exactly as shown in the original (like '101' or '102')\n"
            f"2. Do NOT add new job positions or companies\n"
            f"3. Do NOT modify the company name, position title, dates, or location\n"
            f"4. Do NOT return any skills in your response - I will handle skills separately\n"
            f"5. You MUST include all the achievements for each position\n\n"
            f"RULES:\n{rules_text}\n\n"
            f"Return only the enhanced experiences and a professional summary. DO NOT return any skill information."
        )
        return prompt

    @staticmethod
    def create_manual_response(function_args: Dict[str, Any], req: CVAnalysisRequest) -> Dict[str, Any]:
        """Create a manually constructed response when parse validation fails"""
        utc_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        user_login = "praiseunite"
        logger.info(f"Creating manual response at {utc_time} UTC for user: {user_login}")
        
        # Get AI experiences and fix them
        ai_experiences = function_args.get("experiences", [])
        fixed_experiences = AIService.process_experiences(ai_experiences, req.experiences)
        
        # Create Skill and Experience objects
        skills_objects = req.skills
        experience_objects = []
        
        for exp_data in fixed_experiences:
            try:
                exp_obj = Experiences(**exp_data)
                experience_objects.append(exp_obj)
            except ValidationError:
                # If validation fails, use original experience
                for orig_exp in req.experiences:
                    if orig_exp.id == exp_data.get("id"):
                        experience_objects.append(orig_exp)
                        break
        
        # Create the CVAnalysis object
        try:
            response_model = CVAnalysis(
                experiences=experience_objects,
                skills=skills_objects,
                professionalSummary=function_args.get("professionalSummary", "Experienced professional with strong skills matching the job requirements.")
            )
            
            return response_model.model_dump()
            
        except ValidationError as e:
            logger.error(f"Manual response creation failed: {str(e)}")
            return AIService.create_fallback_response(req)

    @staticmethod
    def create_fallback_response(req: CVAnalysisRequest) -> Dict[str, Any]:
        """Create a fallback response when AI fails"""
        utc_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        user_login = "praiseunite"
        logger.warning(f"Using fallback response due to AI processing errors at {utc_time} UTC for user: {user_login}")
        
        try:
            # Create a CVAnalysis model with the original data
            response_model = CVAnalysis(
                experiences=req.experiences,
                skills=req.skills,
                professionalSummary="Experienced professional with relevant skills matching the job requirements."
            )
            
            return response_model.model_dump()
            
        except ValidationError as e:
            logger.error(f"Fallback response creation failed: {str(e)}")
            
            # Last resort direct dictionary return
            return {
                "experiences": [exp.model_dump() for exp in req.experiences],
                "skills": [skill.model_dump() for skill in req.skills],
                "professionalSummary": "Experienced professional with relevant skills matching the job requirements."
            }