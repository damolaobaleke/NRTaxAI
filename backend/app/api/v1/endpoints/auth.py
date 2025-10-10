"""
Authentication Endpoints
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from app.core.config import settings
from app.core.database import get_database
from app.services.auth import AuthService, create_access_token, create_refresh_token, verify_token, get_current_user
from app.models.user import UserCreate, Token, UserInDB

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=Token)
async def register(
    user_data: UserCreate,
    db = Depends(get_database)
):
    """Register a new user"""
    auth_service = AuthService(db)
    
    # Check if user already exists
    if await auth_service.user_exists(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = await auth_service.create_user(
        email=user_data.email,
        password=user_data.password,
        mfa_enabled=user_data.mfa_enabled
    )
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.id), "email": user.email})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/login", response_model=Token)
async def login(
    email: str,
    password: str,
    db = Depends(get_database)
):
    """Login user"""
    auth_service = AuthService(db)
    
    user = await auth_service.authenticate_user(email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.id), "email": user.email})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db = Depends(get_database)
):
    """Refresh access token"""
    try:
        token_data = verify_token(refresh_token, token_type="refresh")
        
        # Verify user still exists
        user = await db.fetch_one(
            "SELECT id, email FROM users WHERE id = :user_id",
            {"user_id": token_data.user_id}
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create new tokens
        access_token = create_access_token(data={"sub": str(token_data.user_id), "email": token_data.email})
        new_refresh_token = create_refresh_token(data={"sub": str(token_data.user_id), "email": token_data.email})
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/verify-email")
async def verify_email(
    token: str,
    db = Depends(get_database)
):
    """Verify user email (placeholder for future implementation)"""
    # TODO: Implement email verification
    return {"message": "Email verification not implemented yet"}


@router.post("/setup-mfa")
async def setup_mfa(
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(get_database)
):
    """Setup MFA for user (placeholder for future implementation)"""
    # TODO: Implement MFA setup
    return {"message": "MFA setup not implemented yet"}


@router.post("/verify-mfa")
async def verify_mfa(
    token: str,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(get_database)
):
    """Verify MFA token (placeholder for future implementation)"""
    # TODO: Implement MFA verification
    return {"message": "MFA verification not implemented yet"}
