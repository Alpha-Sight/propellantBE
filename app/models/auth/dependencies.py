from fastapi import Header, HTTPException, Request, Depends
from typing import Optional
import httpx
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

# Load XION blockchain API details from environment variables
XION_API_URL = os.getenv("XION_API_URL")
XION_API_KEY = os.getenv("XION_API_KEY", "")

class XionVerificationData(BaseModel):
    transaction_hash: str
    public_key: str
    session_token: str

async def verify_xion_transaction(
    request: Request,
    x_transaction_hash: str = Header(...),
    x_public_key: str = Header(...),
    x_session_token: str = Header(...)
) -> XionVerificationData:
    """
    Verifies that the request headers contain valid XION blockchain credentials.
    
    Args:
        request: The FastAPI request object
        x_transaction_hash: Transaction hash from the blockchain
        x_public_key: User's public key
        x_session_token: Session token from the frontend
        
    Returns:
        XionVerificationData: The validated blockchain data
        
    Raises:
        HTTPException: If validation fails
    """
    # Validate headers are present (FastAPI will handle this via Header(...))
    
    verification_data = XionVerificationData(
        transaction_hash=x_transaction_hash,
        public_key=x_public_key,
        session_token=x_session_token,
    )
    
    # Verify against XION blockchain
    try:
        # Query XION blockchain for transaction details
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{XION_API_URL}/transactions/{x_transaction_hash}",
                headers={"Authorization": f"Bearer {XION_API_KEY}"} if XION_API_KEY else {},
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=401, 
                    detail="Invalid transaction hash or blockchain API error"
                )
            
            transaction_data = response.json()
            
            # Verify public key matches transaction sender
            if transaction_data.get("sender") != x_public_key:
                raise HTTPException(
                    status_code=401,
                    detail="Public key does not match transaction sender"
                )
            
            # Verify transaction status is confirmed
            if transaction_data.get("status") != "confirmed":
                raise HTTPException(
                    status_code=401,
                    detail="Transaction not confirmed on blockchain"
                )
            
            # Add any additional verification logic you need based on the transaction data
            # For example, verifying token amount, transaction time, etc.
            
            # If everything is valid, return the verification data
            return verification_data
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during blockchain verification: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to verify blockchain credentials"
        )