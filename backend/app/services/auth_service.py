"""
Authentication Service
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text

from app.core.config import settings
from app.core.database import get_database
from app.models.user import TokenData, UserInDB

# Password hashing
# Use pbkdf2_sha256 as primary scheme, with bcrypt as fallback
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt"],
    deprecated="auto",
    pbkdf2_sha256__default_rounds=600000,
    pbkdf2_sha256__min_rounds=100000,
    pbkdf2_sha256__max_rounds=1000000
)

# JWT security
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using pbkdf2_sha256"""
    # Using pbkdf2_sha256 which doesn't have the 72-byte limit of bcrypt
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
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
        user_id: str = payload.get("sub") # sub is the subject of the token, which is the user_id
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
    
    result = await db.execute(
        text("""
        SELECT id, email, password_hash, mfa_enabled, is_active, email_verified, created_at
        FROM users 
        WHERE id = :user_id
        """),
        {"user_id": token_data.user_id}
    )
    user = result.fetchone()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return UserInDB(**user._asdict())


async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Get current active user with status checks"""
    
    # Check if account is disabled/banned
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Please contact support."
        )
    
    # Optional: Check if email is verified (uncomment to enforce)
    # if not current_user.email_verified:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Email not verified. Please verify your email to continue."
    #     )
    
    return current_user


class AuthService:
    """Authentication service"""
    
    def __init__(self, db):
        self.db = db
    
    async def authenticate_user(self, email: str, password: str) -> Optional[UserInDB]:
        """Authenticate user with email and password"""
        result = await self.db.execute(
            text("""
            SELECT id, email, password_hash, mfa_enabled, is_active, email_verified, created_at
            FROM users 
            WHERE email = :email
            """),
            {"email": email}
        )
        user = result.fetchone()
        
        if not user:
            return None
            
        if not verify_password(password, user.password_hash):
            return None
            
        return UserInDB(**user._asdict())
    
    async def create_user(self, email: str, password: str, mfa_enabled: bool = False) -> UserInDB:
        """Create a new user in the database"""
        password_hash = get_password_hash(password)
        
        result = await self.db.execute(
            text("""
            INSERT INTO users (email, password_hash, mfa_enabled, is_active, email_verified)
            VALUES (:email, :password_hash, :mfa_enabled, TRUE, FALSE)
            RETURNING id, email, password_hash, mfa_enabled, is_active, email_verified, created_at
            """),
            {
                "email": email,
                "password_hash": password_hash,
                "mfa_enabled": mfa_enabled
            }
        )
        user = result.fetchone()
        
        return UserInDB(**user._asdict())
    
    async def user_exists(self, email: str) -> bool:
        """Check if user exists"""
        result = await self.db.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": email}
        )
        user = result.fetchone()
        return user is not None
    
    async def update_password(self, user_id: UUID, new_password: str) -> bool:
        """Update user password"""
        password_hash = get_password_hash(new_password)
        
        result = await self.db.execute(
            text("""
            UPDATE users 
            SET password_hash = :password_hash
            WHERE id = :user_id
            """),
            {
                "user_id": user_id,
                "password_hash": password_hash
            }
        )
        
        return result > 0
