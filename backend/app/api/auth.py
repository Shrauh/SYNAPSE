"""
SYNAPSE Auth API Router — Register, Login, Logout, Refresh, Me, Change Password.

Tokens are stored in httpOnly cookies (NOT localStorage) for XSS safety.
Rate limiting via slowapi.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.auth_models import User, UserRole
from app.db.database import get_db
from app.services.auth_service import (
    create_access_token,
    create_refresh_token_str,
    create_user,
    decode_access_token,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    hash_password,
    revoke_refresh_token,
    save_refresh_token,
    validate_password_strength,
    validate_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

ACCESS_COOKIE = "synapse_access"
REFRESH_COOKIE = "synapse_refresh"
COOKIE_SECURE = False   # Set True in production (HTTPS)
COOKIE_SAMESITE = "lax"


# ─── Pydantic schemas ─────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    confirm_password: str
    full_name: str = ""

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email address.")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9_]{3,32}$", v):
            raise ValueError("Username: 3-32 chars, letters/digits/underscore only.")
        return v

    @field_validator("password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        errs = validate_password_strength(v)
        if errs:
            raise ValueError(" ".join(errs))
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    message: str
    user: UserResponse


# ─── Dependency: get current user from cookie ─────────────────────────────────

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        # Also check Authorization header for API clients
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated.")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=30 * 60,  # 30 minutes
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=7 * 24 * 3600,  # 7 days
        path="/api/v1/auth/refresh",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth/refresh")


def _user_to_response(u: User) -> UserResponse:
    return UserResponse(
        id=u.id,
        email=u.email,
        username=u.username,
        full_name=u.full_name or "",
        role=u.role if isinstance(u.role, str) else u.role.value,
        is_active=u.is_active,
        created_at=u.created_at,
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    req: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user. Passwords stored as bcrypt hash."""
    if req.password != req.confirm_password:
        raise HTTPException(400, "Passwords do not match.")

    # Check uniqueness
    if await get_user_by_email(db, req.email):
        raise HTTPException(400, "Email already registered.")
    if await get_user_by_username(db, req.username):
        raise HTTPException(400, "Username already taken.")

    # First ever user becomes admin
    from sqlalchemy import func, select as sel
    count_r = await db.execute(sel(func.count()).select_from(User))
    is_first = count_r.scalar_one() == 0
    role = UserRole.admin if is_first else UserRole.user

    user = await create_user(db, req.email, req.username, req.password, req.full_name, role)

    access = create_access_token(user.id, user.role if isinstance(user.role, str) else user.role.value, user.email)
    refresh = create_refresh_token_str()
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")
    await save_refresh_token(db, user.id, refresh, ip, ua)
    _set_auth_cookies(response, access, refresh)

    return TokenResponse(message="Registration successful.", user=_user_to_response(user))


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Login with email + password. Issues httpOnly cookies."""
    user = await get_user_by_email(db, req.email)
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password.")
    if not user.is_active:
        raise HTTPException(403, "Account is deactivated.")

    # Update last_login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    access = create_access_token(user.id, user.role if isinstance(user.role, str) else user.role.value, user.email)
    refresh = create_refresh_token_str()
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")
    await save_refresh_token(db, user.id, refresh, ip, ua)
    _set_auth_cookies(response, access, refresh)

    return TokenResponse(message="Login successful.", user=_user_to_response(user))


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Logout: revoke refresh token + clear cookies."""
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if refresh_token:
        await revoke_refresh_token(db, refresh_token)
    _clear_auth_cookies(response)
    return {"message": "Logged out successfully."}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Issue new access token using refresh token cookie."""
    refresh = request.cookies.get(REFRESH_COOKIE)
    if not refresh:
        raise HTTPException(401, "No refresh token.")
    user = await validate_refresh_token(db, refresh)
    if not user:
        raise HTTPException(401, "Refresh token invalid or expired.")

    # Rotate: revoke old, issue new
    await revoke_refresh_token(db, refresh)
    new_access = create_access_token(user.id, user.role if isinstance(user.role, str) else user.role.value, user.email)
    new_refresh = create_refresh_token_str()
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")
    await save_refresh_token(db, user.id, new_refresh, ip, ua)
    _set_auth_cookies(response, new_access, new_refresh)

    return TokenResponse(message="Token refreshed.", user=_user_to_response(user))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return _user_to_response(current_user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    req: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update display name."""
    if full_name := req.get("full_name"):
        current_user.full_name = full_name[:128]
        await db.commit()
        await db.refresh(current_user)
    return _user_to_response(current_user)


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password (requires current password)."""
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(400, "Current password is incorrect.")
    if req.new_password != req.confirm_new_password:
        raise HTTPException(400, "New passwords do not match.")
    errs = validate_password_strength(req.new_password)
    if errs:
        raise HTTPException(400, " ".join(errs))

    current_user.hashed_password = hash_password(req.new_password)
    await db.commit()
    return {"message": "Password changed successfully."}


@router.post("/forgot-password")
async def forgot_password(req: dict, db: AsyncSession = Depends(get_db)):
    """
    Initiate password reset. 
    NOTE: Email delivery requires SMTP configuration.
    Currently returns a reset token in the response for development.
    """
    import hashlib, secrets
    from datetime import timedelta
    from app.db.auth_models import PasswordResetToken

    email = req.get("email", "").lower().strip()
    user = await get_user_by_email(db, email)
    # Always return 200 to avoid email enumeration
    if not user:
        return {"message": "If that email is registered, a reset link has been sent."}

    token_str = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token_str.encode()).hexdigest()
    prt = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(prt)
    await db.commit()

    # TODO: Send email with reset link
    # reset_url = f"http://localhost:5173/reset-password?token={token_str}"
    # await send_email(user.email, "Reset your SYNAPSE password", reset_url)

    return {
        "message": "If that email is registered, a reset link has been sent.",
        # Dev mode only — remove in production:
        "_dev_reset_token": token_str,
    }


@router.post("/reset-password")
async def reset_password(req: dict, db: AsyncSession = Depends(get_db)):
    """Reset password using token from forgot-password flow."""
    import hashlib
    from sqlalchemy import select as sel
    from app.db.auth_models import PasswordResetToken

    token_str = req.get("token", "")
    new_password = req.get("new_password", "")
    token_hash = hashlib.sha256(token_str.encode()).hexdigest()

    r = await db.execute(
        sel(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used == False,
        )
    )
    prt = r.scalar_one_or_none()
    if not prt or prt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(400, "Invalid or expired reset token.")

    errs = validate_password_strength(new_password)
    if errs:
        raise HTTPException(400, " ".join(errs))

    user = await get_user_by_id(db, prt.user_id)
    if not user:
        raise HTTPException(404, "User not found.")

    user.hashed_password = hash_password(new_password)
    prt.used = True
    await db.commit()
    return {"message": "Password reset successfully. Please log in."}
