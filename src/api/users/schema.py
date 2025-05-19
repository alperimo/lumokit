from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr

#################################################
#### USER AUTHENTICATION SCHEMA ####
#################################################


class UserAuthRequest(BaseModel):
    public_key: str
    signature: str


class UserAuthResponse(BaseModel):
    success: bool


#################################################
#### USER PRO STATUS SCHEMA ####
#################################################


class UserProStatusRequest(BaseModel):
    public_key: str


class UserProStatusResponse(BaseModel):
    is_pro: bool
    days_remaining: Optional[int] = None


#################################################
#### USER PRO UPGRADE SCHEMA ####
#################################################


class ProUpgradeRequest(BaseModel):
    public_key: str
    transaction_signature: str


class ProUpgradeResponse(BaseModel):
    success: bool
    message: str
    premium_end_date: Optional[datetime] = None


#################################################
#### WALLET GENERATION SCHEMA ####
#################################################


class WalletGenerationRequest(BaseModel):
    pass


class WalletGenerationResponse(BaseModel):
    public_key: str
    private_key: str
    encrypted_private_key: str


#################################################
#### PORTFOLIO SCHEMA ####
#################################################


class PortfolioRequest(BaseModel):
    public_key: str


class PortfolioTokenItem(BaseModel):
    address: str
    decimals: int
    balance: int
    uiAmount: float
    chainId: str
    name: str
    symbol: str
    icon: Optional[str] = None
    logoURI: Optional[str] = None
    priceUsd: float
    valueUsd: float


class PortfolioData(BaseModel):
    wallet: str
    totalUsd: float
    items: List[PortfolioTokenItem]


class PortfolioResponse(BaseModel):
    success: bool
    data: Optional[PortfolioData] = None
    error: Optional[str] = None
