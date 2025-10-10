"""
Form Generation Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
from uuid import UUID

from app.core.database import get_database
from app.services.auth import get_current_user
from app.services.form_generator import form_generator
from app.models.user import UserInDB

router = APIRouter()


@router.post("/{return_id}/generate")
async def generate_tax_forms(
    return_id: UUID,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(get_database)
):
    """Generate all applicable tax forms for a return"""
    
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
        
        # Check if tax return has been computed
        if not tax_return.get("totals_json"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tax return must be computed before generating forms"
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
        
        # Prepare user data
        import json
        user_data = {
            "first_name": user_profile.get("first_name"),
            "last_name": user_profile.get("last_name"),
            "itin": user_profile.get("itin"),
            "visa_class": user_profile.get("visa_class"),
            "residency_country": user_profile.get("residency_country"),
            "address_json": json.loads(user_profile.get("address_json", "{}")) if isinstance(user_profile.get("address_json"), str) else user_profile.get("address_json", {})
        }
        
        # Prepare tax data
        tax_data = {
            "tax_year": tax_return["tax_year"],
            "residency_determination": json.loads(tax_return.get("residency_result_json", "{}")) if isinstance(tax_return.get("residency_result_json"), str) else {},
            "treaty_benefits": json.loads(tax_return.get("treaty_json", "{}")) if isinstance(tax_return.get("treaty_json"), str) else {},
            "taxable_income_calculation": {},
            "income_sourcing": {},
            "federal_tax": {},
            "tax_credits": {},
            "final_computation": json.loads(tax_return.get("totals_json", "{}")) if isinstance(tax_return.get("totals_json"), str) else {}
        }
        
        # Days in US (should be stored in user profile or tax return)
        days_data = {
            tax_return["tax_year"]: 300,
            tax_return["tax_year"] - 1: 280,
            tax_return["tax_year"] - 2: 250
        }
        
        # Generate all forms
        forms_result = await form_generator.generate_all_forms(
            tax_data=tax_data,
            user_data=user_data,
            days_data=days_data,
            return_id=str(return_id)
        )
        
        # Store form records in database
        for form_type, form_data in forms_result.get("forms", {}).items():
            if form_data.get("status") == "generated":
                await db.execute(
                    """
                    INSERT INTO forms (return_id, form_type, s3_key, status, version, metadata_json)
                    VALUES (:return_id, :form_type, :s3_key, :status, :version, :metadata)
                    """,
                    {
                        "return_id": str(return_id),
                        "form_type": form_type,
                        "s3_key": form_data.get("file_key"),
                        "status": "generated",
                        "version": 1,
                        "metadata": json.dumps(form_data)
                    }
                )
        
        # Update tax return status
        await db.execute(
            """
            UPDATE tax_returns 
            SET status = 'review'
            WHERE id = :return_id
            """,
            {"return_id": str(return_id)}
        )
        
        return {
            "return_id": str(return_id),
            "forms_generated": forms_result,
            "status": "generated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate forms: {str(e)}"
        )


@router.get("/{return_id}/forms")
async def list_generated_forms(
    return_id: UUID,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(get_database)
):
    """List all generated forms for a return"""
    
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
        
        # Get all forms
        forms = await db.fetch_all(
            """
            SELECT id, form_type, s3_key, status, version, created_at
            FROM forms 
            WHERE return_id = :return_id
            ORDER BY created_at DESC
            """,
            {"return_id": str(return_id)}
        )
        
        form_list = []
        for form in forms:
            form_list.append({
                "id": str(form["id"]),
                "form_type": form["form_type"],
                "s3_key": form["s3_key"],
                "status": form["status"],
                "version": form["version"],
                "created_at": form["created_at"].isoformat() if form["created_at"] else None
            })
        
        return {
            "return_id": str(return_id),
            "forms": form_list,
            "total_forms": len(form_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list forms: {str(e)}"
        )


@router.get("/{return_id}/forms/{form_id}/download")
async def get_form_download_url(
    return_id: UUID,
    form_id: UUID,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get download URL for a generated form"""
    
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
        
        # Get form
        form = await db.fetch_one(
            """
            SELECT * FROM forms 
            WHERE id = :form_id AND return_id = :return_id
            """,
            {"form_id": str(form_id), "return_id": str(return_id)}
        )
        
        if not form:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Form not found"
            )
        
        # Generate pre-signed download URL
        from app.services.s3_service import s3_service
        
        download_url = await s3_service.generate_presigned_download_url(
            file_key=form["s3_key"],
            bucket=settings.S3_BUCKET_PDFS,
            expires_in=3600
        )
        
        return {
            "form_id": str(form_id),
            "form_type": form["form_type"],
            "download_url": download_url,
            "expires_in": 3600
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get download URL: {str(e)}"
        )
