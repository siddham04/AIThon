from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class UserRegister(BaseModel):
    """Loose validation so hackathon demos accept any handle + password."""

    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def _strip_email(cls, v: object) -> str:
        if v is None:
            raise ValueError("email is required")
        s = str(v).strip()
        if not s:
            raise ValueError("email must not be empty")
        return s


class UserLogin(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def _strip_login_email(cls, v: object) -> str:
        if v is None:
            raise ValueError("email is required")
        s = str(v).strip()
        if not s:
            raise ValueError("email must not be empty")
        return s


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserPublic(BaseModel):
    id: int
    email: str
