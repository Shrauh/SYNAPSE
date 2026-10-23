"""
SYNAPSE Auth Service — password hashing, JWT access/refresh tokens.
Uses bcrypt directly (not passlib) + python-jose for JWTs.
"""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt as _bcrypt
from jose import JWTError, jwt  # noqa: F401 — used by JWT helpers below
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.auth_models import RefreshToken, User, UserRole

# ─── Config ────────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "synapse-super-secret-change-in-prod-32chars!!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


# ─── Password helpers (direct bcrypt — works with bcrypt v4 and v5) ───────────
def hash_password(plain: str) -> str:
    """Hash password with bcrypt. Returns a UTF-8 string."""
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    try:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def validate_password_strength(password: str) -> list[str]:
    """Return list of validation errors (empty = OK)."""
    errors: list[str] = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter.")
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter.")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit.")
    return errors


# ─── JWT helpers ───────────────────────────────────────────────────────────────
def create_access_token(user_id: int, role: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "role": role,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token_str() -> str:
    """Generate a cryptographically random refresh token string."""
    return secrets.token_urlsafe(48)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def decode_access_token(token: str) -> dict:
    """Decode and validate JWT. Raises JWTError on failure."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ─── DB helpers ────────────────────────────────────────────────────────────────
async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    r = await db.execute(select(User).where(User.email == email.lower().strip()))
    return r.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    r = await db.execute(select(User).where(User.id == user_id))
    return r.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    r = await db.execute(select(User).where(User.username == username.lower().strip()))
    return r.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    username: str,
    plain_password: str,
    full_name: str = "",
    role: UserRole = UserRole.user,
) -> User:
    user = User(
        email=email.lower().strip(),
        username=username.lower().strip(),
        hashed_password=hash_password(plain_password),
        full_name=full_name,
        role=role,
        is_active=True,
        is_verified=True,  # Skip email verify for now; set False if email configured
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def save_refresh_token(
    db: AsyncSession,
    user_id: int,
    token_str: str,
    ip: str = "",
    ua: str = "",
) -> RefreshToken:
    rt = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(token_str),
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        ip_address=ip[:64],
        user_agent=ua[:256],
    )
    db.add(rt)
    await db.commit()
    return rt


async def revoke_refresh_token(db: AsyncSession, token_str: str) -> bool:
    token_hash = _hash_token(token_str)
    r = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    rt = r.scalar_one_or_none()
    if rt and not rt.revoked:
        rt.revoked = True
        await db.commit()
        return True
    return False


async def validate_refresh_token(db: AsyncSession, token_str: str) -> Optional[User]:
    """Return the User if refresh token is valid, else None."""
    token_hash = _hash_token(token_str)
    r = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
        )
    )
    rt = r.scalar_one_or_none()
    if not rt:
        return None
    if rt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return None
    return await get_user_by_id(db, rt.user_id)
