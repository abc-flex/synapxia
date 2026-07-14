"""
Authentication routes — fully on fastapi-users.

All auth endpoints (`/login`, `/logout`, `/register`, `/me`, …) are the
fastapi-users defaults mounted directly under ``/api/auth``. The custom shim
that previously lived here was removed in favor of the library implementation.

Key customizations:
- ``BcryptPasswordHelper`` — uses passlib bcrypt so existing ``$2b$12$…``
  hashes in the DB keep working (fastapi-users v13 defaults to argon2).
- ``UserManager.authenticate`` — overridden to accept either username OR
  email (default only accepts email).
- ``UserManager.create`` — validates that the referenced ``profile`` and
  ``unit`` exist before persisting (preserves prior register behavior).
"""
import logging
import secrets
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi_users import BaseUserManager, FastAPIUsers, IntegerIDMixin, exceptions, models
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    CookieTransport,
    JWTStrategy,
)
from fastapi_users.authentication.strategy import AccessTokenDatabase, DatabaseStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.password import PasswordHelperProtocol
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyAccessTokenDatabase
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..admin.internal.models import BusinessUnit, Profile, User
from ..core.config import settings
from ..internal.dependencies import get_async_session
from .models import RefreshToken
from .schemas import UserCreate, UserRead, UserUpdate

logger = logging.getLogger(__name__)

# JWT secret + lifetimes come from pydantic-settings (single source of truth).
# The "default secret" warning is emitted from config.py at startup, not here.
SECRET_KEY = settings.jwt_secret


# ==================== Password Helper (bcrypt) ====================

class BcryptPasswordHelper(PasswordHelperProtocol):
    """
    Drop-in PasswordHelper that uses passlib bcrypt instead of fastapi-users'
    default argon2 (pwdlib). Required because the seeded hashes in the users
    table use bcrypt (``$2b$12$…``). Without this swap every login would 401.
    """

    def __init__(self) -> None:
        self.context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_and_update(self, plain_password: str, hashed_password: str) -> Tuple[bool, Optional[str]]:
        verified = self.context.verify(plain_password, hashed_password)
        new_hash: Optional[str] = None
        if verified and self.context.needs_update(hashed_password):
            new_hash = self.context.hash(plain_password)
        return (verified, new_hash)

    def hash(self, password: str) -> str:
        return self.context.hash(password)

    def generate(self) -> str:
        return secrets.token_urlsafe(32)


# ==================== fastapi-users setup ====================

class _UserDatabase(SQLAlchemyUserDatabase):
    """
    Adapter that translates fastapi-users' ``hashed_password`` writes to our
    actual column name ``password_hash``. The ``User`` model exposes
    ``hashed_password`` as a *read-only* SQLAlchemy synonym, which means:
      - on INSERT, ``User(hashed_password=…)`` silently drops the value (the
        synonym's setter doesn't propagate), producing a NULL column → IntegrityError.
      - on UPDATE, ``setattr(user, "hashed_password", …)`` raises ``NotImplementedError``.
    Renaming the key on both paths keeps the model surface clean without
    making the synonym writable.
    """

    @staticmethod
    def _rewrite(d: dict) -> dict:
        if "hashed_password" in d:
            d = dict(d)
            d["password_hash"] = d.pop("hashed_password")
        return d

    async def create(self, create_dict):
        return await super().create(self._rewrite(create_dict))

    async def update(self, user, update_dict):
        return await super().update(user, self._rewrite(update_dict))


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    """SQLAlchemy adapter for fastapi-users."""
    yield _UserDatabase(session, User)


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    """User manager: bcrypt hashing + username-or-email login + FK validation."""

    reset_password_token_secret = SECRET_KEY
    verification_token_secret = SECRET_KEY

    async def authenticate(self, credentials) -> Optional[User]:
        """
        Override the default authenticate() to accept the OAuth2
        ``username`` field as either a username or an email address.
        """
        identifier = credentials.username

        # Try email first (fastapi-users' default lookup)
        try:
            user = await self.get_by_email(identifier)
        except exceptions.UserNotExists:
            user = None

        # Fall back to username lookup via the underlying session
        if user is None:
            stmt = select(User).where(User.username == identifier)
            result = await self.user_db.session.execute(stmt)
            user = result.scalars().first()

        if user is None:
            # Hash anyway to keep timing roughly constant
            self.password_helper.hash(credentials.password)
            return None

        verified, updated_password_hash = self.password_helper.verify_and_update(
            credentials.password, user.hashed_password
        )
        if not verified:
            return None

        if updated_password_hash is not None:
            await self.user_db.update(user, {"hashed_password": updated_password_hash})

        return user

    async def create(
        self,
        user_create,
        safe: bool = False,
        request=None,
    ) -> User:
        """Validate FKs to profiles/business_units before delegating to the default create."""
        session: AsyncSession = self.user_db.session

        profile_code = getattr(user_create, "profile", None)
        if profile_code:
            result = await session.execute(select(Profile).where(Profile.code == profile_code))
            if result.scalars().first() is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Profile '{profile_code}' does not exist",
                )

        unit_code = getattr(user_create, "unit", None)
        if unit_code:
            result = await session.execute(select(BusinessUnit).where(BusinessUnit.code == unit_code))
            if result.scalars().first() is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Business unit '{unit_code}' does not exist",
                )

        return await super().create(user_create, safe=safe, request=request)

    async def on_after_register(self, user: User, request=None) -> None:
        logger.info(f"User {user.username} registered successfully")

    async def on_after_login(self, user: User, request=None, response=None) -> None:
        logger.info(f"User {user.username} logged in")

    async def on_after_forgot_password(self, user: User, token: str, request=None) -> None:
        logger.info(f"Password reset requested for {user.username}")

    async def on_after_request_verify(self, user: User, token: str, request=None) -> None:
        logger.info(f"Verification requested for {user.username}")


async def get_user_manager(user_db=Depends(get_user_db)):
    """Provide UserManager with the bcrypt-backed password helper."""
    yield UserManager(user_db, password_helper=BcryptPasswordHelper())


# Bearer transport — tokenUrl points to where the UI POSTs OAuth2 form creds
bearer_transport = BearerTransport(tokenUrl="/api/auth/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.jwt_secret,
        lifetime_seconds=settings.jwt_lifetime_seconds,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


# ==================== Refresh-token backend ====================
# Long-lived refresh tokens persisted in the `refresh_tokens` table. The UI
# trades a refresh token for a fresh access token via POST /api/auth/refresh/login
# when the access token expires — no password re-prompt needed.

async def get_access_token_db(
    session: AsyncSession = Depends(get_async_session),
) -> AccessTokenDatabase[RefreshToken]:
    yield SQLAlchemyAccessTokenDatabase(session, RefreshToken)


def get_refresh_strategy(
    access_token_db: AccessTokenDatabase[RefreshToken] = Depends(get_access_token_db),
) -> DatabaseStrategy:
    return DatabaseStrategy(
        database=access_token_db,
        lifetime_seconds=settings.jwt_refresh_lifetime_seconds,
    )


# Separate transport so the refresh router lives at /api/auth/refresh/* and
# its tokens never overlap with the access-token bearer scheme on /api/*.
refresh_transport = BearerTransport(tokenUrl="/api/auth/refresh/login")

refresh_backend = AuthenticationBackend(
    name="refresh",
    transport=refresh_transport,
    get_strategy=get_refresh_strategy,
)


# ==================== Cookie backend (for browser/SSR clients) ====================
# Same JWT strategy, different transport: the token rides in an HTTP-only
# cookie instead of an Authorization header. This unlocks SSR-side fetches
# from Astro (server can read cookies; localStorage is browser-only).
cookie_transport = CookieTransport(
    cookie_name="auth_token",
    cookie_max_age=settings.jwt_lifetime_seconds,
    cookie_httponly=True,
    cookie_secure=settings.app_env == "production",  # HTTPS-only in prod
    cookie_samesite="lax",
    cookie_domain=settings.cookie_domain or None,
    cookie_path="/",
)

cookie_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,  # SAME JWT — single source of truth
)


fastapi_users = FastAPIUsers[User, int](
    get_user_manager, [auth_backend, refresh_backend, cookie_backend]
)

# Dependencies exported for other routes
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)


# ==================== Router assembly ====================
# Mount all fastapi-users routers directly under /api/auth (no /fastapi prefix).
router = APIRouter(prefix="/api/auth", tags=["authentication"])

# POST /login, POST /logout  (short-lived access-token JWT)
router.include_router(fastapi_users.get_auth_router(auth_backend))

# POST /refresh/login, POST /refresh/logout  (long-lived refresh tokens
# stored in refresh_tokens table; trade refresh→access via this endpoint)
router.include_router(
    fastapi_users.get_auth_router(refresh_backend),
    prefix="/refresh",
)

# POST /cookie/login, POST /cookie/logout  (Set-Cookie / Clear-Cookie of
# `auth_token`; used by the browser/SSR. JWT itself is identical to the
# bearer flow.)
router.include_router(
    fastapi_users.get_auth_router(cookie_backend),
    prefix="/cookie",
)

# POST /refresh — trade a valid refresh token for a fresh access token.
# fastapi-users doesn't ship this endpoint (refresh-token flows vary across
# apps) but we compose it from its primitives — refresh_strategy.read_token
# resolves the user; jwt_strategy.write_token mints the new access token.
# No password re-prompt, no DB session row created.
@router.post("/refresh")
async def refresh_access_token(
    authorization: str = Header(...),
    user_manager: UserManager = Depends(get_user_manager),
    refresh_strategy: DatabaseStrategy = Depends(get_refresh_strategy),
) -> dict:
    """Exchange a refresh token (Bearer) for a new short-lived access token."""
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[len("bearer "):].strip()

    user = await refresh_strategy.read_token(token, user_manager)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    new_access_token = await get_jwt_strategy().write_token(user)
    return {"access_token": new_access_token, "token_type": "bearer"}


# POST /register
router.include_router(fastapi_users.get_register_router(UserRead, UserCreate))

# GET /me, PATCH /me, GET /{id}, PATCH /{id}, DELETE /{id}
# NOTE: PATCH /me lets the authenticated user change their own password by
# sending {"password": "..."}. There is no old-password verification — having
# a valid JWT is the proof of identity.
router.include_router(fastapi_users.get_users_router(UserRead, UserUpdate))


__all__ = [
    "router",
    "current_active_user",
    "current_superuser",
    "fastapi_users",
]
