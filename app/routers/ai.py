from fastapi import APIRouter, HTTPException
import httpx
from app.models.requests import CVAnalysisRequest
from app.services.input_service import InputService
from app.services.rules_service import RulesService
from app.services.ai_service import AIService  # Make sure this import is correct (singular, not plural)

router = APIRouter()

@router.post("/cv-analysis")
async def cv_analysis(cv_data: CVAnalysisRequest):
    """Endpoint to rewrite CV content using AI model"""
    try:
        # Validate input
        validated_data = InputService.validate_input(cv_data)
        
        # Get rules
        rules = RulesService.get_rules()
        
        # Communicate with AI using tool-based approach
        # This now returns a validated CVAnalysis object directly
        cv_analysis = await AIService.rewrite_content(validated_data, rules)
        
        # Format the response
        formatted_response = {
            "work_experience": [exp.model_dump() for exp in cv_analysis.work_experience],
            "skills": cv_analysis.skills,
            "professional_summary": cv_analysis.professional_summary
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
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")