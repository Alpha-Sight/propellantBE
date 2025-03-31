from fastapi import APIRouter, HTTPException, Depends
import httpx
import os
from app.models.requests import CVAnalysisRequest
from app.services.input_service import InputService
from app.services.rules_service import RulesService
from app.services.ai_service import AIService
from app.auth.blockchainAuth import (
    verify_blockchain_credentials, 
    mock_verify_blockchain_credentials, 
    BlockchainCredentials,
    deduct_cv_credit
)

# Determine if we're in development mode
DEV_MODE = os.getenv("ENVIRONMENT", "development") == "development"

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
        print(f"Processing CV analysis request with transaction: {blockchain_auth.transaction_hash}")
        print(f"User public key: {blockchain_auth.public_key}")
        
        # Validate input
        validated_data = InputService.validate_input(cv_data)
        
        # Get rules
        rules = RulesService.get_rules()
        
        # Process with AI service
        cv_analysis = await AIService.rewrite_content(validated_data, rules)
        
        # Format the response
        formatted_response = {
            "work_experience": [exp.model_dump() for exp in cv_analysis.work_experience],
            "skills": cv_analysis.skills,
            "professional_summary": cv_analysis.professional_summary,
            "transaction_hash": blockchain_auth.transaction_hash,  # Include for reference
        }
        
        # CV generation successful, now deduct a credit
        deduction_result = await deduct_cv_credit(
            blockchain_auth.public_key,
            blockchain_auth.session_token
        )
        
        # Add credit deduction information to the response
        formatted_response["credit_deduction"] = {
            "success": deduction_result.get("success", False),
            "remaining_credits": deduction_result.get("remaining_credits", 0),
            "transaction_hash": deduction_result.get("transaction_hash", "")
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