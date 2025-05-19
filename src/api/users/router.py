from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from settings.db import get_db

from .controllers import (authenticate_with_signature, check_user_pro_status,
                          generate_new_wallet, get_wallet_portfolio_ds,
                          process_pro_upgrade)
from .schema import (PortfolioRequest, PortfolioResponse, ProUpgradeRequest,
                     ProUpgradeResponse, UserAuthRequest, UserAuthResponse,
                     UserProStatusRequest, UserProStatusResponse,
                     WalletGenerationRequest, WalletGenerationResponse)

router = APIRouter()

#############################################
#############################################
### User Login Endpoint ###
#############################################
#############################################


@router.post("/login", response_model=UserAuthResponse)
async def authenticate_user_signature(
    user_request: UserAuthRequest, db: Session = Depends(get_db)
):
    success = await authenticate_with_signature(user_request, db)
    return {"success": success}


################################################
################################################
### User Pro Status Endpoint ###
################################################
################################################


@router.post("/verify-pro", response_model=UserProStatusResponse)
async def verify_user_pro_status(
    user_request: UserProStatusRequest, db: Session = Depends(get_db)
):
    try:
        result = await check_user_pro_status(user_request, db)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error verifying pro status: {str(e)}"
        )


################################################
################################################
### User Pro Upgrade Endpoint ###
################################################
################################################


@router.post("/upgrade-pro", response_model=ProUpgradeResponse)
async def upgrade_to_pro(
    upgrade_request: ProUpgradeRequest, db: Session = Depends(get_db)
):
    try:
        result = await process_pro_upgrade(upgrade_request, db)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing pro upgrade: {str(e)}"
        )


################################################
################################################
### Wallet Generation Endpoint ###
################################################
################################################


@router.get("/generate-wallet", response_model=WalletGenerationResponse)
async def generate_wallet():
    """
    Generates a new Solana wallet
    """
    try:
        result = await generate_new_wallet()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating wallet: {str(e)}"
        )


################################################
################################################
### Wallet Portfolio ###
################################################
################################################


@router.get("/wal-portfolio/{public_key}", response_model=PortfolioResponse)
async def get_portfolio2(public_key: str):
    """
    Get wallet portfolio directly from Solana RPC
    """
    try:
        result = await get_wallet_portfolio_ds(public_key)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving portfolio: {str(e)}"
        )
