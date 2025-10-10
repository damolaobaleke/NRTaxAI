"""
Tax Returns Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID

from app.core.database import get_database
from app.services.auth import get_current_active_user
from app.models.user import UserInDB
from app.models.tax_return import (
    TaxReturn, TaxReturnCreate, TaxReturnUpdate, TaxReturnSummary,
    Document, Validation, Computation
)

router = APIRouter()


@router.post("/", response_model=TaxReturn)
async def create_tax_return(
    return_data: TaxReturnCreate,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Create new tax return"""
    
    # Check if return already exists for this year
    existing = await db.fetch_one(
        """
        SELECT id FROM tax_returns 
        WHERE user_id = :user_id AND tax_year = :tax_year
        """,
        {
            "user_id": current_user.id,
            "tax_year": return_data.tax_year
        }
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tax return already exists for this year"
        )
    
    # Create tax return
    tax_return = await db.fetch_one(
        """
        INSERT INTO tax_returns (user_id, tax_year, status)
        VALUES (:user_id, :tax_year, :status)
        RETURNING id, user_id, tax_year, status, ruleset_version,
                  residency_result_json, treaty_json, totals_json,
                  created_at, updated_at
        """,
        {
            "user_id": current_user.id,
            "tax_year": return_data.tax_year,
            "status": return_data.status
        }
    )
    
    return TaxReturn(**tax_return)


@router.get("/", response_model=List[TaxReturn])
async def list_tax_returns(
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """List tax returns for current user"""
    
    returns = await db.fetch_all(
        """
        SELECT id, user_id, tax_year, status, ruleset_version,
               residency_result_json, treaty_json, totals_json,
               created_at, updated_at
        FROM tax_returns 
        WHERE user_id = :user_id
        ORDER BY tax_year DESC
        """,
        {"user_id": current_user.id}
    )
    
    return [TaxReturn(**ret) for ret in returns]


@router.get("/{return_id}", response_model=TaxReturn)
async def get_tax_return(
    return_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get tax return details"""
    
    tax_return = await db.fetch_one(
        """
        SELECT id, user_id, tax_year, status, ruleset_version,
               residency_result_json, treaty_json, totals_json,
               created_at, updated_at
        FROM tax_returns 
        WHERE id = :return_id AND user_id = :user_id
        """,
        {
            "return_id": return_id,
            "user_id": current_user.id
        }
    )
    
    if not tax_return:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax return not found"
        )
    
    return TaxReturn(**tax_return)


@router.get("/{return_id}/summary", response_model=TaxReturnSummary)
async def get_tax_return_summary(
    return_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get comprehensive tax return summary"""
    
    # Get tax return
    tax_return = await db.fetch_one(
        """
        SELECT id, user_id, tax_year, status, ruleset_version,
               residency_result_json, treaty_json, totals_json,
               created_at, updated_at
        FROM tax_returns 
        WHERE id = :return_id AND user_id = :user_id
        """,
        {
            "return_id": return_id,
            "user_id": current_user.id
        }
    )
    
    if not tax_return:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax return not found"
        )
    
    # Get documents
    documents = await db.fetch_all(
        """
        SELECT id, user_id, return_id, s3_key, doc_type, source,
               status, extracted_json, validation_json, created_at
        FROM documents 
        WHERE return_id = :return_id
        ORDER BY created_at ASC
        """,
        {"return_id": return_id}
    )
    
    # Get validations
    validations = await db.fetch_all(
        """
        SELECT id, return_id, severity, field, code, message, data_path, created_at
        FROM validations 
        WHERE return_id = :return_id
        ORDER BY created_at DESC
        """,
        {"return_id": return_id}
    )
    
    # Get computations
    computations = await db.fetch_all(
        """
        SELECT id, return_id, line_code, description, amount, source, created_at
        FROM computations 
        WHERE return_id = :return_id
        ORDER BY line_code ASC
        """,
        {"return_id": return_id}
    )
    
    # Calculate totals from computations
    total_income = sum(comp["amount"] for comp in computations if comp["line_code"].startswith("income"))
    total_tax = sum(comp["amount"] for comp in computations if comp["line_code"].startswith("tax"))
    total_withholding = sum(comp["amount"] for comp in computations if comp["line_code"].startswith("withholding"))
    refund_or_balance_due = total_withholding - total_tax
    
    return TaxReturnSummary(
        return_info=TaxReturn(**tax_return),
        documents=[Document(**doc) for doc in documents],
        validations=[Validation(**val) for val in validations],
        computations=[Computation(**comp) for comp in computations],
        total_income=total_income if total_income > 0 else None,
        total_tax=total_tax if total_tax > 0 else None,
        total_withholding=total_withholding if total_withholding > 0 else None,
        refund_or_balance_due=refund_or_balance_due
    )


@router.post("/{return_id}/compute")
async def compute_tax(
    return_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Compute tax calculations for return"""
    
    # TODO: Implement tax computation engine
    return {"message": "Tax computation not implemented yet"}


@router.get("/{return_id}/validation")
async def get_validation_status(
    return_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get validation status and issues for return"""
    
    validations = await db.fetch_all(
        """
        SELECT id, return_id, severity, field, code, message, data_path, created_at
        FROM validations 
        WHERE return_id = :return_id
        ORDER BY severity DESC, created_at DESC
        """,
        {"return_id": return_id}
    )
    
    return {
        "validations": [Validation(**val) for val in validations],
        "status": "valid" if not validations else "has_issues"
    }


@router.post("/{return_id}/what-if")
async def what_if_analysis(
    return_id: UUID,
    scenario_data: dict,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Run what-if scenario analysis"""
    
    # TODO: Implement what-if analysis
    return {"message": "What-if analysis not implemented yet"}


@router.post("/{return_id}/generate")
async def generate_forms(
    return_id: UUID,
    form_types: List[str],
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Generate tax forms (1040NR, 8843, W-8BEN, 1040-V)"""
    
    # TODO: Implement PDF form generation
    return {"message": "Form generation not implemented yet"}


@router.get("/{return_id}/download")
async def download_form(
    return_id: UUID,
    form_type: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Download generated tax form"""
    
    # TODO: Implement form download
    return {"message": "Form download not implemented yet"}
