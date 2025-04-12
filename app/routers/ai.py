from fastapi import APIRouter, HTTPException, Depends
import httpx
import os
import logging
from app.models.requests import CVAnalysisRequest, CVAnalysis
from app.services.input_service import InputService
from app.services.rules_service import RulesService
from app.services.ai_service import AIService
from app.auth.blockchainAuth import (
    verify_blockchain_credentials, 
    mock_verify_blockchain_credentials, 
    BlockchainCredentials,
    deduct_cv_credit
)

# Configure logging
logger = logging.getLogger(__name__)

# Determine if we're in development mode
DEV_MODE = os.getenv("ENVIRONMENT", "development") == "development"

# Initialize FastAPI router
router = APIRouter()

@router.post("/cv-analysis")
async def cv_analysis(
    cv_data: CVAnalysisRequest,
    blockchain_auth: BlockchainCredentials = Depends(
        mock_verify_blockchain_credentials if DEV_MODE else verify_blockchain_credentials
    )
):
    """
    Generate an optimized CV based on job description and existing resume.
    Requires valid XION blockchain authentication.
    """
    try:
        # Log the transaction for auditing
        logger.info(f"Processing CV analysis request for user: {blockchain_auth.user_address}")
        
        # Validate input
        validated_data = InputService.validate_input(cv_data)

        # Get rules for processing
        rules = RulesService.get_rules()

        # Process with AI service - returns a CVAnalysis model
        cv_analysis_result = await AIService.rewrite_content(validated_data, rules)
        
        # Ensure the response matches the expected CVAnalysis format
        formatted_response = CVAnalysis(
            experiences=cv_analysis_result.get("experiences", []),
            skills=cv_analysis_result.get("skills", []),
            professionalSummary=cv_analysis_result.get("professionalSummary", "")
        )

        # Deduct a credit for the CV generation
        deduction_result = await deduct_cv_credit(
            blockchain_auth.user_address,
            blockchain_auth.secure_token
        )
        
        if not deduction_result.get("success", False):
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to deduct credit: {deduction_result.get('error', 'Unknown error')}"
            )
        
        # Add credit deduction information to the response
        response_with_credits = formatted_response.dict()
        # response_with_credits["remaining_credits"] = deduction_result.get("credits_remaining", 0)
        # response_with_credits["transaction_hash"] = deduction_result.get("tx_hash", "")

        # Return the final response
        return response_with_credits

    except httpx.HTTPStatusError as e:
        # Handle HTTP errors from external calls
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # Add general exception handling
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")