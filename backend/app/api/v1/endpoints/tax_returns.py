"""
Tax Returns Endpoints
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID
from sqlalchemy import text

from app.core.database import get_database

# Set up logging
logger = logging.getLogger(__name__)
from app.services.auth_service import get_current_active_user
from app.models.user import UserInDB
from app.models.tax_return import (
    TaxReturn, TaxReturnCreate, TaxReturnUpdate, TaxReturnSummary,
    Document, Validation, Computation
)
from sqlalchemy import text

router = APIRouter()


@router.post("/", response_model=TaxReturn)
async def create_tax_return(
    return_data: TaxReturnCreate,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Create new tax return"""
    
    # Check if return already exists for this year
    result = await db.execute(
        text("""
                SELECT id FROM tax_returns 
                WHERE user_id = :user_id AND tax_year = :tax_year
            """),
            {
                "user_id": current_user.id,
                "tax_year": return_data.tax_year
            }
    )
    existing = result.fetchone()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tax return already exists for this year"
        )
    
    # Create tax return
    result = await db.execute(
        text("""
            INSERT INTO tax_returns (user_id, tax_year, status)
            VALUES (:user_id, :tax_year, :status)
            RETURNING id, user_id, tax_year, status, ruleset_version,
                    residency_result_json, treaty_json, totals_json,
                    created_at, updated_at
            """),
        {
            "user_id": current_user.id,
            "tax_year": return_data.tax_year,
            "status": return_data.status
        }
    )
    tax_return = result.fetchone()
    print(tax_return._asdict())
    return TaxReturn(**tax_return._asdict())


@router.get("/", response_model=List[TaxReturn])
async def list_tax_returns(
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """List tax returns for current user"""
    
    result = await db.execute(
        text("""
        SELECT id, user_id, tax_year, status, ruleset_version,
               residency_result_json, treaty_json, totals_json,
               created_at, updated_at
        FROM tax_returns 
        WHERE user_id = :user_id
        ORDER BY tax_year DESC
        """),
        {"user_id": current_user.id}
    )
    returns = result.fetchall()
    
    return [TaxReturn(**ret._asdict()) for ret in returns]


@router.get("/{return_id}", response_model=TaxReturn)
async def get_tax_return(
    return_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get tax return details"""
    
    result = await db.execute(
    text("""
        SELECT id, user_id, tax_year, status, ruleset_version,
               residency_result_json, treaty_json, totals_json,
               created_at, updated_at
        FROM tax_returns 
        WHERE id = :return_id AND user_id = :user_id
        """),
        {
            "return_id": return_id,
            "user_id": current_user.id
        }
    )
    tax_return = result.fetchone()
    
    if not tax_return:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax return not found"
        )
    
    return TaxReturn(**tax_return._asdict())


@router.get("/{return_id}/summary", response_model=TaxReturnSummary)
async def get_tax_return_summary(
    return_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get comprehensive tax return summary"""
    logger.info(f"Getting tax return summary for return_id: {return_id}")
    try:
        # Get tax return
        result = await db.execute(
            text("""
            SELECT id, user_id, tax_year, status, ruleset_version,
                   residency_result_json, treaty_json, totals_json,
                   created_at, updated_at
            FROM tax_returns 
            WHERE id = :return_id AND user_id = :user_id
            """),
            {
                "return_id": return_id,
                "user_id": current_user.id
            }
        )
        tax_return = result.fetchone()
        # print(tax_return)
        # print(tax_return._asdict())
        
        if not tax_return:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tax return not found"
            )
        
        # Convert tax return to dict from tuple if needed
        if isinstance(tax_return, tuple):
            # If it's a tuple, we need to map it to field names
            field_names = ['id', 'user_id', 'tax_year', 'status', 'ruleset_version', 
                          'residency_result_json', 'treaty_json', 'totals_json', 
                          'created_at', 'updated_at']
            tax_return_dict = dict(zip(field_names, tax_return))
        else:
            tax_return_dict = tax_return._asdict()
        
        # Get documents
        result = await db.execute(
            text("""
            SELECT id, user_id, return_id, s3_key, doc_type, source,
                   status, extracted_json, validation_json, created_at
            FROM documents 
            WHERE return_id = :return_id
            ORDER BY created_at ASC
            """),
            {"return_id": return_id}
        )
        documents = result.fetchall()
        
        # Convert documents to dicts - use _asdict() if available, otherwise convert tuple to dict strictly
        documents_list = []
        for doc in documents:
            if hasattr(doc, '_asdict'):
                documents_list.append(doc._asdict())
            else:
                # Fallback for tuples - map to field names
                field_names = ['id', 'user_id', 'return_id', 's3_key', 'doc_type', 'source', 
                              'status', 'extracted_json', 'validation_json', 'created_at']
                documents_list.append(dict(zip(field_names, doc)))
        
        # Get validations
        result = await db.execute(
            text("""
            SELECT id, return_id, severity, field, code, message, data_path, created_at
            FROM validations 
            WHERE return_id = :return_id
            ORDER BY created_at DESC
            """),
            {"return_id": return_id}
        )
        validations = result.fetchall()
        
        # Convert validations to dicts - use _asdict() if available, otherwise convert tuple to dict strictly
        validations_list = []
        for val in validations:
            if hasattr(val, '_asdict'):
                validations_list.append(val._asdict())
            else:
                # Fallback for tuples - map to field names
                field_names = ['id', 'return_id', 'severity', 'field', 'code', 'message', 'data_path', 'created_at']
                validations_list.append(dict(zip(field_names, val)))
        
        # Get computations
        result = await db.execute(
            text("""
            SELECT id, return_id, line_code, description, amount, source, created_at
            FROM computations 
            WHERE return_id = :return_id
            ORDER BY line_code ASC
            """),
            {"return_id": return_id}
        )
        computations = result.fetchall()
        
        # Convert computations to dicts - use _asdict() if available, otherwise convert tuple to dict strictly
        computations_list = []
        for comp in computations:
            if hasattr(comp, '_asdict'):
                computations_list.append(comp._asdict())
            else:
                # Fallback for tuples - map to field names
                field_names = ['id', 'return_id', 'line_code', 'description', 'amount', 'source', 'created_at']
                computations_list.append(dict(zip(field_names, comp)))
        
        # Calculate totals from computations
        try:
            total_income = sum(comp['amount'] for comp in computations_list if comp.get('line_code', '').startswith("income"))
        except Exception as e:
            total_income = 0
            
        try:
            total_tax = sum(comp['amount'] for comp in computations_list if comp.get('line_code', '').startswith("tax"))
        except Exception as e:
            total_tax = 0
            
        try:
            total_withholding = sum(comp['amount'] for comp in computations_list if comp.get('line_code', '').startswith("withholding"))
        except Exception as e:
            total_withholding = 0
            
        refund_or_balance_due = total_withholding - total_tax
        
        try:
            return_info = TaxReturn(**tax_return_dict)
        except Exception as e:
            raise
            
        try:
            doc_list = [Document(**doc) for doc in documents_list]
        except Exception as e:
            raise
            
        try:
            val_list = [Validation(**val) for val in validations_list]
        except Exception as e:
            raise
            
        try:
            comp_list = [Computation(**comp) for comp in computations_list]
        except Exception as e:
            raise
        
        return TaxReturnSummary(
            return_info=return_info,
            documents=doc_list,
            validations=val_list,
            computations=comp_list,
            total_income=total_income if total_income > 0 else None,
            total_tax=total_tax if total_tax > 0 else None,
            total_withholding=total_withholding if total_withholding > 0 else None,
            refund_or_balance_due=refund_or_balance_due
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tax return summary: {str(e)}"
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
    
    result = await db.execute(
        text("""
        SELECT id, return_id, severity, field, code, message, data_path, created_at
        FROM validations 
        WHERE return_id = :return_id
        ORDER BY severity DESC, created_at DESC
        """),
        {"return_id": return_id}
    )
    validations = result.fetchall()
    
    return {
        "validations": [Validation(**val._asdict()) for val in validations],
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
