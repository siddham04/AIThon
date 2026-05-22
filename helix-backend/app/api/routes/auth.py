from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...config import get_settings
from ...database import get_db
from ...schemas.auth import TokenResponse, UserLogin, UserRegister
from ...services.security import create_access_token, hash_password, verify_password
from ...sqla_models import User
from ..deps import get_current_user

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> TokenResponse:
    """Register a new account, or sign in when email+password already match."""
    existing = db.scalars(select(User).where(User.email == str(payload.email))).first()
    if existing:
        if verify_password(payload.password, existing.hashed_password):
            token = create_access_token(str(existing.id))
            return TokenResponse(access_token=token)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "That username is already registered — sign in or pick a different one.",
        )
    user = User(email=str(payload.email), hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    """Sign in. Auto-register on first login only when hackathon auth is enabled."""
    settings = get_settings()
    user = db.scalars(select(User).where(User.email == str(payload.email))).first()
    if user is None:
        if not settings.allow_hackathon_auth:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
        user = User(
            email=str(payload.email),
            hashed_password=hash_password(payload.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token(str(user.id))
        return TokenResponse(access_token=token)
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@router.post("/guest", response_model=TokenResponse)
def guest(db: Session = Depends(get_db)) -> TokenResponse:
    """One-click throwaway account (disabled when HELIX_PRODUCTION=1)."""
    if not get_settings().allow_hackathon_auth:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Guest access is disabled on this deployment",
        )
    handle = f"guest-{secrets.token_hex(4)}@helix.demo"
    while db.scalars(select(User).where(User.email == handle)).first() is not None:
        handle = f"guest-{secrets.token_hex(4)}@helix.demo"
    user = User(
        email=handle,
        hashed_password=hash_password(secrets.token_urlsafe(24)),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(user: User = Depends(get_current_user)) -> TokenResponse:
    """Rotate access token (new jti) while the current bearer token is still valid."""
    return TokenResponse(access_token=create_access_token(str(user.id)))
