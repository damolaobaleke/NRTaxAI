"""
Tax Computation Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date

from app.core.database import get_database
from app.services.auth_service import get_current_user
from app.services.tax_rules_engine import get_tax_rules_engine
from app.services.document_aggregation_service import document_aggregation_service
from app.models.user import UserInDB
from sqlalchemy import text

router = APIRouter()


@router.post("/{return_id}/compute")
async def compute_tax_return(
    return_id: UUID,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(get_database)
):
    """Compute tax return using rules engine"""
    
    try:
        # Get tax return
        result = await db.execute(
            text("""
            SELECT * FROM tax_returns 
            WHERE id = :return_id AND user_id = :user_id
            """),
            {"return_id": str(return_id), "user_id": str(current_user.id)}
        )
        tax_return = result.fetchone()
        
        if not tax_return:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tax return not found"
            )
        
        # Get user profile
        result = await db.execute(
            text("SELECT * FROM user_profiles WHERE user_id = :user_id"),
            {"user_id": str(current_user.id)}
        )
        user_profile = result.fetchone()
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Get documents for this return
        result = await db.execute(
            text("""
            SELECT * FROM documents 
            WHERE return_id = :return_id AND status = 'extracted'
            """),
            {"return_id": str(return_id)}
        )
        documents = result.fetchall()
        
        if not documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No extracted documents found for this return"
            )
        
        # Aggregate income data from documents 
        income_data = await document_aggregation_service.aggregate_income_from_documents(documents)
        withholding_data = await document_aggregation_service.aggregate_withholding_from_documents(
            documents,
            visa_type=user_profile.get("visa_class"),
            entry_date=user_data.get("entry_date"),
            tax_year=tax_return["tax_year"]
        )
        
        # Prepare user data
        user_data = {
            "visa_type": user_profile.get("visa_class"),
            "country_code": user_profile.get("residency_country"),
            "entry_date": user_profile.get("entry_date", "2020-01-01"),  # Should be in profile
            "years_in_status": 2,  # Should be calculated
            "state_code": user_profile.get("address_json", {}).get("state", "CA")
        }
        
        # Days in US (should be collected from user)
        days_in_us = {
            tax_return["tax_year"]: 300,
            tax_return["tax_year"] - 1: 280,
            tax_return["tax_year"] - 2: 250
        }
        
        # Get tax rules engine
        tax_engine = get_tax_rules_engine(tax_return["tax_year"])
        
        # Compute tax return
        computation_result = await tax_engine.compute_complete_tax_return(
            user_data=user_data,
            income_data=income_data,
            withholding_data=withholding_data,
            days_in_us=days_in_us
        )
        
        # Update tax return with computation
        await db.execute(
            text("""
            UPDATE tax_returns 
            SET status = 'computing',
                ruleset_version = :ruleset_version,
                residency_result_json = :residency_result,
                treaty_json = :treaty_json,
                totals_json = :totals_json,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :return_id
            """),
            {
                "return_id": str(return_id),
                "ruleset_version": computation_result["ruleset_version"],
                "residency_result": str(computation_result["residency_determination"]),
                "treaty_json": str(computation_result["treaty_benefits"]),
                "totals_json": str(computation_result["final_computation"])
            }
        )
        
        return {
            "return_id": str(return_id),
            "status": "computed",
            "computation_result": computation_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute tax return: {str(e)}"
        )


@router.get("/{return_id}/summary")
async def get_tax_return_summary(
    return_id: UUID,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get tax return summary"""
    
    try:
        # Get tax return
        result = await db.execute(
            text("""
            SELECT * FROM tax_returns 
            WHERE id = :return_id AND user_id = :user_id
            """),
            {"return_id": str(return_id), "user_id": str(current_user.id)}
        )
        tax_return = result.fetchone()
        
        if not tax_return:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tax return not found"
            )
        
        # Get documents count
        result = await db.execute(
            text("""
            SELECT COUNT(*) as count FROM documents 
            WHERE return_id = :return_id
            """),
            {"return_id": str(return_id)}
        )
        documents_count = result.fetchone()
        
        return {
            "return_id": str(return_id),
            "tax_year": tax_return["tax_year"],
            "status": tax_return["status"],
            "ruleset_version": tax_return["ruleset_version"],
            "residency_result": tax_return["residency_result_json"],
            "treaty_benefits": tax_return["treaty_json"],
            "totals": tax_return["totals_json"],
            "documents_count": documents_count["count"],
            "created_at": tax_return["created_at"].isoformat() if tax_return["created_at"] else None,
            "updated_at": tax_return["updated_at"].isoformat() if tax_return["updated_at"] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tax return summary: {str(e)}"
        )
