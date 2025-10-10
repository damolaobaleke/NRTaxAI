"""
Audit Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_database
from app.services.auth import get_current_user
from app.services.audit_service import get_audit_service
from app.models.user import UserInDB

router = APIRouter()


@router.get("/returns/{return_id}")
async def get_return_audit_logs(
    return_id: UUID,
    limit: int = 100,
    offset: int = 0,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get audit logs for a tax return"""
    
    try:
        # Verify return ownership
        tax_return = await db.fetch_one(
            """
            SELECT * FROM tax_returns 
            WHERE id = :return_id AND user_id = :user_id
            """,
            {"return_id": str(return_id), "user_id": str(current_user.id)}
        )
        
        if not tax_return:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tax return not found"
            )
        
        # Get audit logs
        audit_service = await get_audit_service()
        logs = await audit_service.get_audit_logs_for_return(
            return_id=str(return_id),
            limit=limit,
            offset=offset
        )
        
        return logs
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit logs: {str(e)}"
        )


@router.get("/returns/{return_id}/verify")
async def verify_audit_chain(
    return_id: UUID,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(get_database)
):
    """Verify audit log chain integrity"""
    
    try:
        # Verify return ownership
        tax_return = await db.fetch_one(
            """
            SELECT * FROM tax_returns 
            WHERE id = :return_id AND user_id = :user_id
            """,
            {"return_id": str(return_id), "user_id": str(current_user.id)}
        )
        
        if not tax_return:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tax return not found"
            )
        
        # Verify chain
        audit_service = await get_audit_service()
        verification = await audit_service.verify_audit_chain(str(return_id))
        
        return verification
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify audit chain: {str(e)}"
        )


@router.post("/returns/{return_id}/export")
async def export_audit_trail(
    return_id: UUID,
    format: str = "json",
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(get_database)
):
    """Export audit trail for tax return"""
    
    try:
        # Verify return ownership (or operator access)
        tax_return = await db.fetch_one(
            """
            SELECT * FROM tax_returns 
            WHERE id = :return_id AND user_id = :user_id
            """,
            {"return_id": str(return_id), "user_id": str(current_user.id)}
        )
        
        if not tax_return:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tax return not found"
            )
        
        # Export audit trail
        audit_service = await get_audit_service()
        export_result = await audit_service.export_audit_trail(
            return_id=str(return_id),
            format=format
        )
        
        return export_result
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export audit trail: {str(e)}"
        )


@router.post("/returns/{return_id}/bundle")
async def create_audit_bundle(
    return_id: UUID,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(get_database)
):
    """Create complete audit bundle for tax return"""
    
    try:
        # Verify return ownership (or operator access)
        tax_return = await db.fetch_one(
            """
            SELECT * FROM tax_returns 
            WHERE id = :return_id AND user_id = :user_id
            """,
            {"return_id": str(return_id), "user_id": str(current_user.id)}
        )
        
        if not tax_return:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tax return not found"
            )
        
        # Create bundle
        audit_service = await get_audit_service()
        bundle = await audit_service.create_audit_bundle(str(return_id))
        
        return bundle
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create audit bundle: {str(e)}"
        )
