"""Authentication configuration and routes."""
import os
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi_users import BaseUserManager, IntegerIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from sqlmodel import Session, select
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..admin.internal.models import User, Role, BusinessUnit
from ..internal import get_db_session
from .schemas import UserRead, UserCreate, UserUpdate

logger = logging.getLogger(__name__)

# ==================== Password Hashing ====================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ==================== JWT Configuration ====================
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
if SECRET_KEY == "your-secret-key-change-in-production":
    logger.warning(
        "⚠️  Using default SECRET_KEY. Set SECRET_KEY environment variable in production!")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# ==================== JWT Token Functions ====================


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str):
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except JWTError:
        return None

# ==================== User Manager ====================


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    """Custom user manager for SQLModel integration."""

    reset_password_token_secret = SECRET_KEY
    verification_token_secret = SECRET_KEY

    def __init__(self, user_db, session: Session):
        super().__init__(user_db)
        self.session = session

    async def on_after_register(self, user: User, request=None) -> None:
        """Called after user registration."""
        logger.info(f"User {user.username} registered successfully")

    async def on_after_forgot_password(self, user: User, request=None) -> None:
        """Called after reset password request."""
        logger.info(f"Password reset requested for {user.username}")

    async def on_after_request_verify(self, user: User, request=None) -> None:
        """Called after email verification request."""
        logger.info(f"Verification requested for {user.username}")

# ==================== Authentication Dependency ====================


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_db_session)
) -> User:
    """
    Get the current authenticated user from JWT token.

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_exception

    user = session.get(User, user_id)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Get current user and verify they are a superuser."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not enough permissions")
    return current_user

# ==================== Routes ====================
router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/login", response_model=dict)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_db_session)
):
    """
    Login endpoint - returns JWT access token.

    Username can be either username or email.
    """
    # Find user by username or email
    stmt = select(User).where(
        (User.username == form_data.username) | (
            User.email == form_data.username)
    )
    user = session.exec(stmt).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Update last login
    user.last_login_at = datetime.utcnow()
    session.add(user)
    session.commit()

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})

    logger.info(f"User {user.username} logged in")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "menu_role": user.menu_role,
            "business_unit": user.business_unit,
        }
    }


@router.post("/register", response_model=UserRead, status_code=201)
def register(
    user_data: UserCreate,
    session: Session = Depends(get_db_session)
):
    """
    Register a new user.

    Validates:
    - Username and email are unique
    - Role and business_unit exist
    """
    # Check username uniqueness
    existing_user = session.exec(
        select(User).where(User.username == user_data.username)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_data.username}' already registered"
        )

    # Check email uniqueness
    existing_email = session.exec(
        select(User).where(User.email == user_data.email)
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{user_data.email}' already registered"
        )

    # Validate role exists
    role = session.get(Role, user_data.menu_role)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{user_data.menu_role}' does not exist"
        )

    # Validate business_unit exists
    business_unit = session.get(BusinessUnit, user_data.business_unit)
    if not business_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Business unit '{user_data.business_unit}' does not exist"
        )

    # Create user with hashed password
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        menu_role=user_data.menu_role,
        business_unit=user_data.business_unit,
        is_active=True,
        is_superuser=False,
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    logger.info(f"New user registered: {new_user.username}")

    return new_user


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_active_user)):
    """Get current user profile."""
    return current_user


@router.post("/change-password")
def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db_session)
):
    """Change password for current user."""
    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )

    current_user.password_hash = hash_password(new_password)
    current_user.updated_at = datetime.utcnow()

    session.add(current_user)
    session.commit()

    logger.info(f"Password changed for user {current_user.username}")

    return {"message": "Password changed successfully"}


@router.post("/logout")
def logout(current_user: User = Depends(get_current_active_user)):
    """
    Logout endpoint - returns success message.

    Note: JWT tokens are stateless, so logout is client-side by removing the token.
    This endpoint is provided for API consistency.
    """
    logger.info(f"User {current_user.username} logged out")
    return {"message": "Logged out successfully"}
