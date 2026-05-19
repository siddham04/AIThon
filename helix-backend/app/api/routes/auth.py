from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...database import get_db
from ...schemas.auth import TokenResponse, UserLogin, UserRegister
from ...services.security import create_access_token, hash_password, verify_password
from ...sqla_models import User

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> TokenResponse:
    exists = db.scalars(select(User).where(User.email == str(payload.email))).first()
    if exists:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")
    user = User(email=str(payload.email), hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalars(select(User).where(User.email == str(payload.email))).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)
