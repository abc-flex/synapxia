"""
Authentication configuration and routes (Phase 2: fastapi-users integration).

Combines fastapi-users machinery with backward-compatibility shim to preserve
the existing /api/auth contract for the Astro UI.
"""
import os
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi_users import BaseUserManager, IntegerIDMixin, FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..admin.internal.models import User, Profile, BusinessUnit
from ..internal.dependencies import get_async_session
from .schemas import UserRead, UserCreate, UserUpdate

# Bcrypt context — matches the hashes already stored in the DB ($2b$12$…)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger = logging.getLogger(__name__)

# ==================== JWT Configuration ====================
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
if SECRET_KEY == "your-secret-key-change-in-production":
    logger.warning(
        "⚠️  Using default SECRET_KEY. Set SECRET_KEY environment variable in production!")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# ==================== fastapi-users setup ====================


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    """Dependency that provides SQLAlchemy user database."""
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    """Custom user manager for fastapi-users with bcrypt password hashing."""

    reset_password_token_secret = SECRET_KEY
    verification_token_secret = SECRET_KEY

    async def on_after_register(self, user: User, request=None) -> None:
        """Called after user registration."""
        logger.info(f"User {user.username} registered successfully")

    async def on_after_forgot_password(self, user: User, request=None) -> None:
        """Called after reset password request."""
        logger.info(f"Password reset requested for {user.username}")

    async def on_after_request_verify(self, user: User, request=None) -> None:
        """Called after email verification request."""
        logger.info(f"Verification requested for {user.username}")


async def get_user_manager(user_db=Depends(get_user_db)):
    """Dependency that provides the user manager."""
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="/api/auth/login")


def get_jwt_strategy() -> JWTStrategy:
    """JWT strategy for authentication."""
    return JWTStrategy(
        secret=SECRET_KEY,
        lifetime_seconds=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# Initialize fastapi-users with the JWT backend
fastapi_users = FastAPIUsers[User, int](get_user_manager, [auth_backend])

# Export auth dependencies for use in other routes
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)

# ==================== Routes ====================
router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Include fastapi-users auto-generated routers at /api/auth/fastapi/*
# These provide a complete auth system with password reset, email verification, etc.
fastapi_users_routers = fastapi_users.get_auth_router(auth_backend)
router.include_router(fastapi_users_routers, prefix="/fastapi")

# ==================== Backward-compatibility shim ====================
# The Astro UI expects the old contract:
# POST /api/auth/login → {access_token, token_type, user: {id, username, email, ...}}
# These endpoints delegate to fastapi-users while preserving the old response shape.


@router.post("/login", response_model=dict)
async def login(
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Login endpoint - backward-compatible with Astro UI.

    Returns JWT access token + user profile object (for UI convenience).
    Username can be either username or email.
    """
    # Query user by username or email
    stmt = select(User).where(
        (User.username == username) | (User.email == username)
    )
    result = await session.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password against the bcrypt hash stored in the DB
    if not pwd_context.verify(password, user.password_hash):
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

    # Generate JWT token using fastapi-users' JWT strategy
    jwt_strategy = get_jwt_strategy()
    access_token = await jwt_strategy.write_token(user)

    logger.info(f"User {user.username} logged in")

    # Return token + user profile (preserves Astro UI contract)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "profile": user.profile,
            "unit": user.unit,
        }
    }


@router.post("/register", response_model=UserRead, status_code=201)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Register a new user.

    Validates:
    - Username and email are unique
    - Profile and unit exist
    """
    # Check username uniqueness
    result = await session.execute(
        select(User).where(User.username == user_data.username)
    )
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{user_data.username}' already registered"
        )

    # Check email uniqueness
    result = await session.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{user_data.email}' already registered"
        )

    # Validate profile exists
    result = await session.execute(
        select(Profile).where(Profile.code == user_data.profile)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Profile '{user_data.profile}' does not exist"
        )

    # Validate unit exists
    result = await session.execute(
        select(BusinessUnit).where(BusinessUnit.code == user_data.unit)
    )
    unit = result.scalars().first()
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Business unit '{user_data.unit}' does not exist"
        )

    # Hash password with bcrypt (consistent with existing hashes in the DB)
    hashed_password = pwd_context.hash(user_data.password)

    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        profile=user_data.profile,
        unit=user_data.unit,
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    logger.info(f"New user registered: {new_user.username}")

    return new_user


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(current_active_user)):
    """Get current user profile."""
    return current_user


@router.post("/change-password")
async def change_password(
    old_password: str = Form(...),
    new_password: str = Form(...),
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Change password for current user."""
    # Verify old password against bcrypt hash
    if not pwd_context.verify(old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )

    # Hash and update new password
    current_user.password_hash = pwd_context.hash(new_password)

    session.add(current_user)
    await session.commit()

    logger.info(f"Password changed for user {current_user.username}")

    return {"message": "Password changed successfully"}


@router.post("/logout")
async def logout(current_user: User = Depends(current_active_user)):
    """
    Logout endpoint - returns success message.

    Note: JWT tokens are stateless, so logout is client-side by removing the token.
    This endpoint is provided for API consistency.
    """
    logger.info(f"User {current_user.username} logged out")

    return {"message": "Successfully logged out"}


__all__ = [
    "router",
    "current_active_user",
    "current_superuser",
    "fastapi_users",
]
