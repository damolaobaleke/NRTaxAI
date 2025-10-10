"""
Authentication Service
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.database import get_database
from app.models.user import TokenData, UserInDB

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT security
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> TokenData:
    """Verify JWT token and return token data"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        token_type_claim: str = payload.get("type")
        
        if user_id is None or email is None or token_type_claim != token_type:
            raise credentials_exception
            
        token_data = TokenData(user_id=UUID(user_id), email=email)
        return token_data
        
    except JWTError:
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_database)
) -> UserInDB:
    """Get current authenticated user"""
    token_data = verify_token(credentials.credentials)
    
    user = await db.fetch_one(
        """
        SELECT id, email, password_hash, mfa_enabled, created_at
        FROM users 
        WHERE id = :user_id
        """,
        {"user_id": token_data.user_id}
    )
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return UserInDB(**user)


async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Get current active user (placeholder for future user status checks)"""
    return current_user


class AuthService:
    """Authentication service"""
    
    def __init__(self, db):
        self.db = db
    
    async def authenticate_user(self, email: str, password: str) -> Optional[UserInDB]:
        """Authenticate user with email and password"""
        user = await self.db.fetch_one(
            """
            SELECT id, email, password_hash, mfa_enabled, created_at
            FROM users 
            WHERE email = :email
            """,
            {"email": email}
        )
        
        if not user:
            return None
            
        if not verify_password(password, user["password_hash"]):
            return None
            
        return UserInDB(**user)
    
    async def create_user(self, email: str, password: str, mfa_enabled: bool = False) -> UserInDB:
        """Create new user"""
        password_hash = get_password_hash(password)
        
        user_id = await self.db.fetch_one(
            """
            INSERT INTO users (email, password_hash, mfa_enabled)
            VALUES (:email, :password_hash, :mfa_enabled)
            RETURNING id, email, password_hash, mfa_enabled, created_at
            """,
            {
                "email": email,
                "password_hash": password_hash,
                "mfa_enabled": mfa_enabled
            }
        )
        
        return UserInDB(**user_id)
    
    async def user_exists(self, email: str) -> bool:
        """Check if user exists"""
        user = await self.db.fetch_one(
            "SELECT id FROM users WHERE email = :email",
            {"email": email}
        )
        return user is not None
    
    async def update_password(self, user_id: UUID, new_password: str) -> bool:
        """Update user password"""
        password_hash = get_password_hash(new_password)
        
        result = await self.db.execute(
            """
            UPDATE users 
            SET password_hash = :password_hash
            WHERE id = :user_id
            """,
            {
                "user_id": user_id,
                "password_hash": password_hash
            }
        )
        
        return result > 0
