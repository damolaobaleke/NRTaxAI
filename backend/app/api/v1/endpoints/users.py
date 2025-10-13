"""
Users Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional

from app.core.database import get_database
from app.services.auth_service import get_current_user, get_current_active_user
from app.models.user import (
    User, UserInDB, UserProfile, UserProfileCreate, UserProfileUpdate, 
    UserProfileWithITIN, UserUpdate
)

router = APIRouter()


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Get current user information"""
    return User(
        id=current_user.id,
        email=current_user.email,
        mfa_enabled=current_user.mfa_enabled,
        created_at=current_user.created_at
    )


@router.put("/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Update current user information"""
    
    # Build update query dynamically
    update_fields = []
    update_values = {"user_id": current_user.id}
    
    if user_update.mfa_enabled is not None:
        update_fields.append("mfa_enabled = :mfa_enabled")
        update_values["mfa_enabled"] = user_update.mfa_enabled
    
    if not update_fields:
        return User(
            id=current_user.id,
            email=current_user.email,
            mfa_enabled=current_user.mfa_enabled,
            created_at=current_user.created_at
        )
    
    # Execute update
    query = f"""
        UPDATE users 
        SET {', '.join(update_fields)}
        WHERE id = :user_id
        RETURNING id, email, password_hash, mfa_enabled, created_at
    """
    
    updated_user = await db.fetch_one(query, update_values)
    
    return User(
        id=updated_user["id"],
        email=updated_user["email"],
        mfa_enabled=updated_user["mfa_enabled"],
        created_at=updated_user["created_at"]
    )


@router.get("/me/profile", response_model=UserProfileWithITIN)
async def get_current_user_profile(
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get current user profile with decrypted PII"""
    
    profile = await db.fetch_one(
        """
        SELECT 
            up.user_id,
            up.first_name,
            up.last_name,
            up.dob,
            up.residency_country,
            up.visa_class,
            up.ssn_last4,
            up.address_json,
            up.phone,
            up.itin,
            up.created_at,
            up.updated_at
        FROM user_profiles up
        WHERE up.user_id = :user_id
        """,
        {"user_id": current_user.id}
    )
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # TODO: Decrypt ITIN using KMS service
    # For now, return as-is (will be encrypted in production)
    if profile["itin"]:
        decrypted_itin = profile["itin"]
    else:
        decrypted_itin = None
    
    return UserProfileWithITIN(
        user_id=profile["user_id"],
        first_name=profile["first_name"],
        last_name=profile["last_name"],
        dob=profile["dob"],
        residency_country=profile["residency_country"],
        visa_class=profile["visa_class"],
        ssn_last4=profile["ssn_last4"],
        address_json=profile["address_json"],
        phone=profile["phone"],
        itin=decrypted_itin,
        created_at=profile["created_at"],
        updated_at=profile["updated_at"]
    )


@router.post("/me/profile", response_model=UserProfile)
async def create_user_profile(
    profile_data: UserProfileCreate,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Create user profile"""
    
    # Check if profile already exists
    existing_profile = await db.fetch_one(
        "SELECT user_id FROM user_profiles WHERE user_id = :user_id",
        {"user_id": current_user.id}
    )
    
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists"
        )
    
    # TODO: Encrypt ITIN using KMS service if it exists
    # For now, store as-is (will be encrypted in production)
    encrypted_itin = profile_data.itin
    
    profile = await db.fetch_one(
        """
        INSERT INTO user_profiles (
            user_id, first_name, last_name, dob, residency_country,
            visa_class, itin, ssn_last4, address_json, phone
        )
        VALUES (
            :user_id, :first_name, :last_name, :dob, :residency_country,
            :visa_class, :itin, :ssn_last4, :address_json, :phone
        )
        RETURNING user_id, first_name, last_name, dob, residency_country,
                  visa_class, ssn_last4, address_json, phone, created_at, updated_at
        """,
        {
            "user_id": current_user.id,
            "first_name": profile_data.first_name,
            "last_name": profile_data.last_name,
            "dob": profile_data.dob,
            "residency_country": profile_data.residency_country,
            "visa_class": profile_data.visa_class,
            "itin": encrypted_itin,
            "ssn_last4": profile_data.ssn_last4,
            "address_json": profile_data.address_json,
            "phone": profile_data.phone
        }
    )
    
    return UserProfile(**profile)


@router.put("/me/profile", response_model=UserProfile)
async def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Update user profile"""
    
    print(profile_data.model_dump())
    # Build update query dynamically
    update_fields = ["updated_at = CURRENT_TIMESTAMP"]
    update_values = {"user_id": current_user.id}
    
    if profile_data.first_name is not None:
        update_fields.append("first_name = :first_name")
        update_values["first_name"] = profile_data.first_name
    
    if profile_data.last_name is not None:
        update_fields.append("last_name = :last_name")
        update_values["last_name"] = profile_data.last_name
    
    if profile_data.dob is not None:
        update_fields.append("dob = :dob")
        update_values["dob"] = profile_data.dob
    
    if profile_data.residency_country is not None:
        update_fields.append("residency_country = :residency_country")
        update_values["residency_country"] = profile_data.residency_country
    
    if profile_data.visa_class is not None:
        update_fields.append("visa_class = :visa_class")
        update_values["visa_class"] = profile_data.visa_class
    
    if profile_data.ssn_last4 is not None:
        update_fields.append("ssn_last4 = :ssn_last4")
        update_values["ssn_last4"] = profile_data.ssn_last4
    
    if profile_data.address_json is not None:
        update_fields.append("address_json = :address_json")
        update_values["address_json"] = profile_data.address_json
    
    if profile_data.phone is not None:
        update_fields.append("phone = :phone")
        update_values["phone"] = profile_data.phone
    
    if profile_data.itin is not None:
        # TODO: Encrypt ITIN using KMS service
        update_fields.append("itin = :itin")
        update_values["itin"] = profile_data.itin
    
    # Execute update
    query = f"""
        UPDATE user_profiles 
        SET {', '.join(update_fields)}
        WHERE user_id = :user_id
        RETURNING user_id, first_name, last_name, dob, residency_country,
                  visa_class, ssn_last4, address_json, phone, created_at, updated_at
    """
    
    updated_profile = await db.fetch_one(query, update_values)
    
    if not updated_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return UserProfile(**updated_profile)
