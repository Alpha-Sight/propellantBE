from fastapi import APIRouter, HTTPException, Depends
import httpx
import os
import logging
from app.models.requests import CVAnalysisRequest
from app.services.input_service import InputService
from app.services.rules_service import RulesService
from app.services.ai_service import AIService

# Configure logging
logger = logging.getLogger(__name__)

# Determine if we're in development mode
DEV_MODE = os.getenv("ENVIRONMENT", "development") == "development"

router = APIRouter()

@router.post("/cv-analysis")
async def cv_analysis(
    cv_data: CVAnalysisRequest,
):
    """
    Generate an optimized CV based on job description and existing resume.
    """
    try:
        # Log the transaction for auditing
        # logger.info(f"Processing CV analysis request for user: {blockchain_auth.user_address}")
        
        # Validate input
        validated_data = InputService.validate_input(cv_data)
        
        # Get rules
        rules = RulesService.get_rules()
        
        # Process with AI service - returns a dict, not an object
        cv_analysis_dict = await AIService.rewrite_content(validated_data, rules)
        
        # Format the response - use dict access instead of attribute access
        formatted_response = {
            "experiences": cv_analysis_dict.get("experiences", []),
            "skills": cv_analysis_dict.get("skills", []),
            "professionalSummary": cv_analysis_dict.get("professionalSummary", "")
        }
        
        # Return the formatted response
        return formatted_response
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # Add general exception handling
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")