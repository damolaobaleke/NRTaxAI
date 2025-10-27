"""
Authorization Endpoints for Form 8879 Signatures
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.core.database import get_database
from app.services.auth_service import get_current_user
from app.services.authorization_service import get_authorization_service
from app.models.user import UserInDB

router = APIRouter()


class TaxpayerSignature(BaseModel):
    pin: str  # 5-digit self-selected PIN
    signature_method: str = "e-sign"  # e-sign, phone, wet-sign


class OperatorSignature(BaseModel):
    pin: str  # 5-digit ERO PIN


@router.get("/pending")
async def get_pending_authorizations(
    current_user: UserInDB = Depends(get_current_user)
):
    """Get pending authorizations for current user"""
    
    try:
        auth_service = await get_authorization_service()
        
        authorizations = await auth_service.get_pending_authorizations(
            user_id=str(current_user.id)
        )
        
        return {
            "authorizations": authorizations,
            "total": len(authorizations)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending authorizations: {str(e)}"
        )


@router.get("/{authorization_id}")
async def get_authorization_status(
    authorization_id: UUID,
    current_user: UserInDB = Depends(get_current_user)
):
    """Get authorization status"""
    
    try:
        auth_service = await get_authorization_service()
        
        auth_status = await auth_service.get_authorization_status(
            authorization_id=str(authorization_id),
            user_id=str(current_user.id)
        )
        
        return auth_status
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get authorization status: {str(e)}"
        )


@router.post("/{authorization_id}/sign/taxpayer")
async def sign_as_taxpayer(
    authorization_id: UUID,
    signature: TaxpayerSignature,
    request: Request,
    current_user: UserInDB = Depends(get_current_user)
):
    """Taxpayer signs Form 8879"""
    
    try:
        auth_service = await get_authorization_service()
        
        # Get client IP address
        ip_address = request.client.host if request.client else None
        
        result = await auth_service.sign_authorization_taxpayer(
            authorization_id=str(authorization_id),
            user_id=str(current_user.id),
            pin=signature.pin,
            signature_method=signature.signature_method,
            ip_address=ip_address
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sign authorization: {str(e)}"
        )


@router.post("/{authorization_id}/sign/operator")
async def sign_as_operator(
    authorization_id: UUID,
    signature: OperatorSignature,
    operator_id: str = "dummy-operator-id"  # TODO: Get from auth token
):
    """Operator signs Form 8879 as preparer"""
    
    try:
        auth_service = await get_authorization_service()
        
        result = await auth_service.sign_authorization_operator(
            authorization_id=str(authorization_id),
            operator_id=operator_id,
            pin=signature.pin
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sign authorization: {str(e)}"
        )


@router.post("/{authorization_id}/revoke")
async def revoke_authorization(
    authorization_id: UUID,
    reason: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """Revoke an authorization"""
    
    try:
        auth_service = await get_authorization_service()
        
        result = await auth_service.revoke_authorization(
            authorization_id=str(authorization_id),
            user_id=str(current_user.id),
            reason=reason
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke authorization: {str(e)}"
        )
