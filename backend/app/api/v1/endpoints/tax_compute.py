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
from app.models.user import UserInDB

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
        
        # Get user profile
        user_profile = await db.fetch_one(
            "SELECT * FROM user_profiles WHERE user_id = :user_id",
            {"user_id": str(current_user.id)}
        )
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Get documents for this return
        documents = await db.fetch_all(
            """
            SELECT * FROM documents 
            WHERE return_id = :return_id AND status = 'extracted'
            """,
            {"return_id": str(return_id)}
        )
        
        if not documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No extracted documents found for this return"
            )
        
        # Aggregate income data from documents
        income_data = await _aggregate_income_data(documents)
        withholding_data = await _aggregate_withholding_data(documents)
        
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
            """
            UPDATE tax_returns 
            SET status = 'computing',
                ruleset_version = :ruleset_version,
                residency_result_json = :residency_result,
                treaty_json = :treaty_json,
                totals_json = :totals_json,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :return_id
            """,
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
        
        # Get documents count
        documents_count = await db.fetch_one(
            """
            SELECT COUNT(*) as count FROM documents 
            WHERE return_id = :return_id
            """,
            {"return_id": str(return_id)}
        )
        
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


async def _aggregate_income_data(documents: list) -> Dict[str, Any]:
    """Aggregate income data from documents"""
    import json
    
    income_data = {
        "wages": 0,
        "interest": 0,
        "dividends": 0,
        "self_employment": 0,
        "scholarship": 0,
        "fellowship": 0,
        "teaching": 0,
        "research": 0,
        "us_work_days": 0,
        "total_work_days": 0,
        "us_bank_interest": 0,
        "us_corp_dividends": 0,
        "us_self_employment": 0
    }
    
    for doc in documents:
        if not doc.get("extracted_json"):
            continue
        
        try:
            extracted_data = json.loads(doc["extracted_json"])
            fields = extracted_data.get("extracted_fields", {})
            
            # W-2 wages
            if doc["doc_type"] == "W2":
                wages = fields.get("wages", {}).get("value")
                if wages:
                    income_data["wages"] += float(wages.replace(",", "").replace("$", ""))
                income_data["us_work_days"] += 250  # Assume full year
                income_data["total_work_days"] += 250
            
            # 1099-INT interest
            elif doc["doc_type"] == "1099INT":
                interest = fields.get("interest_income", {}).get("value")
                if interest:
                    amount = float(interest.replace(",", "").replace("$", ""))
                    income_data["interest"] += amount
                    income_data["us_bank_interest"] += amount
            
            # 1099-NEC self-employment
            elif doc["doc_type"] == "1099NEC":
                nonemployee_comp = fields.get("nonemployee_compensation", {}).get("value")
                if nonemployee_comp:
                    amount = float(nonemployee_comp.replace(",", "").replace("$", ""))
                    income_data["self_employment"] += amount
                    income_data["us_self_employment"] += amount
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            continue
    
    return income_data


async def _aggregate_withholding_data(documents: list) -> Dict[str, Any]:
    """Aggregate withholding data from documents"""
    import json
    
    withholding_data = {
        "federal_income_tax": 0,
        "social_security_tax": 0,
        "medicare_tax": 0,
        "state_income_tax": 0
    }
    
    for doc in documents:
        if not doc.get("extracted_json"):
            continue
        
        try:
            extracted_data = json.loads(doc["extracted_json"])
            fields = extracted_data.get("extracted_fields", {})
            
            # Federal withholding
            federal_tax = fields.get("federal_income_tax_withheld", {}).get("value")
            if federal_tax:
                withholding_data["federal_income_tax"] += float(federal_tax.replace(",", "").replace("$", ""))
            
            # Social Security tax
            ss_tax = fields.get("social_security_tax_withheld", {}).get("value")
            if ss_tax:
                withholding_data["social_security_tax"] += float(ss_tax.replace(",", "").replace("$", ""))
            
            # Medicare tax
            medicare_tax = fields.get("medicare_tax_withheld", {}).get("value")
            if medicare_tax:
                withholding_data["medicare_tax"] += float(medicare_tax.replace(",", "").replace("$", ""))
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            continue
    
    return withholding_data
