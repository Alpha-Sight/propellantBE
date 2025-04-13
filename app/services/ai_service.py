import json
import os
import logging
from typing import Dict, List, Any
from datetime import datetime
from openai import AsyncOpenAI
from dotenv import load_dotenv
from app.models.requests import CVAnalysisRequest, CVAnalysis, Skill, Experiences

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Load environment variables
load_dotenv()

# API credentials
UNIFY_URL = os.getenv("UNIFY_URL")
UNIFY_API_KEY = os.getenv("UNIFY_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")

# Initialize client
client = AsyncOpenAI(
    base_url=UNIFY_URL,
    api_key=UNIFY_API_KEY
)

class AIService:
    @staticmethod
    def edit_cv():
        """Very simple function definition for AI tool"""
        return {
            "type": "function",
            "function": {
                "name": "provide_edited_cv",
                "description": "Edit the CV to better match the job description",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "exp1_description": {
                            "type": "string",
                            "description": "Enhanced description for experience 1"
                        },
                        "exp1_achievements": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Enhanced achievements for experience 1"
                        },
                        "exp2_description": {
                            "type": "string",
                            "description": "Enhanced description for experience 2"
                        },
                        "exp2_achievements": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Enhanced achievements for experience 2"
                        },
                        "professional_summary": {
                            "type": "string",
                            "description": "Professional summary for the candidate"
                        }
                    },
                    "required": ["exp1_description", "exp1_achievements", "exp2_description", "exp2_achievements", "professional_summary"]
                }
            }
        }

    @classmethod
    async def rewrite_content(cls, req: CVAnalysisRequest, rules: dict = None) -> dict:
        """Ultra-simplified approach that hard-codes what we need"""
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"Current Date and Time: {current_time}")
        logger.info(f"User: praiseunite")
        
        try:
            # Simple format for the prompt
            job_desc = req.jobDescription
            
            # Experience 1
            exp1 = req.experiences[0]
            exp1_text = (
                f"EXPERIENCE 1:\n"
                f"Position: {exp1.position}\n"
                f"Company: {exp1.company}\n"
                f"Period: {exp1.startDate} to {exp1.endDate}\n"
                f"Location: {exp1.location}\n"
                f"Current Description: {exp1.description}\n"
                f"Current Achievements:\n"
            )
            for achievement in exp1.achievements:
                exp1_text += f"- {achievement}\n"
            
            # Experience 2
            exp2 = req.experiences[1]
            exp2_text = (
                f"EXPERIENCE 2:\n"
                f"Position: {exp2.position}\n"
                f"Company: {exp2.company}\n"
                f"Period: {exp2.startDate} to {exp2.endDate}\n"
                f"Location: {exp2.location}\n"
                f"Current Description: {exp2.description}\n"
                f"Current Achievements:\n"
            )
            for achievement in exp2.achievements:
                exp2_text += f"- {achievement}\n"
            
            # Skills
            skills_text = ", ".join([f"{skill.name} ({skill.level})" for skill in req.skills])
            
            # Simple prompt
            prompt = (
                f"TASK: Enhance this resume to match this job description.\n\n"
                f"JOB DESCRIPTION:\n{job_desc}\n\n"
                f"SKILLS: {skills_text}\n\n"
                f"{exp1_text}\n{exp2_text}\n\n"
                f"INSTRUCTIONS:\n"
                f"1. Rewrite the description for BOTH experiences to be more impressive\n"
                f"2. Enhance the achievements for BOTH experiences\n"
                f"3. Create a strong professional summary\n"
                f"4. DO NOT change company names, titles, dates, or locations\n"
                f"5. Use powerful language and specific metrics where possible"
            )
            
            # Send request to AI
            logger.info(f"Sending request to AI...")
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                tools=[cls.edit_cv()],
                tool_choice="auto"
            )
            
            # Process response
            tool_calls = response.choices[0].message.tool_calls
            if not tool_calls:
                logger.warning(f"No tool calls received - returning fallback")
                return cls._fallback_response(req)
            
            # Extract function arguments
            function_args = json.loads(tool_calls[0].function.arguments)
            
            # Log what we got
            logger.info(f"Received AI response, extracting enhanced content...")
            
            # Extract enhancements
            exp1_description = function_args.get("exp1_description", exp1.description)
            exp1_achievements = function_args.get("exp1_achievements", exp1.achievements)
            exp2_description = function_args.get("exp2_description", exp2.description)
            exp2_achievements = function_args.get("exp2_achievements", exp2.achievements)
            summary = function_args.get("professional_summary", "Experienced professional with relevant skills.")
            
            # Create enhanced experiences
            enhanced_experiences = []
            
            # Add Experience 1
            exp1_dict = exp1.model_dump()
            exp1_dict["description"] = exp1_description
            exp1_dict["achievements"] = exp1_achievements
            enhanced_experiences.append(exp1_dict)
            
            # Add Experience 2
            exp2_dict = exp2.model_dump()
            exp2_dict["description"] = exp2_description
            exp2_dict["achievements"] = exp2_achievements
            enhanced_experiences.append(exp2_dict)
            
            # Final result
            result = {
                "experiences": enhanced_experiences,
                "skills": [skill.model_dump() for skill in req.skills],
                "professionalSummary": summary
            }
            
            logger.info(f"Successfully created enhanced CV with all experiences")
            return result
            
        except Exception as e:
            logger.error(f"Error processing CV: {str(e)}")
            return cls._fallback_response(req)
    
    @staticmethod
    def _fallback_response(req: CVAnalysisRequest) -> dict:
        """Simple fallback response"""
        return {
            "experiences": [exp.model_dump() for exp in req.experiences],
            "skills": [skill.model_dump() for skill in req.skills],
            "professionalSummary": "Experienced professional with skills matching the job requirements."
        }