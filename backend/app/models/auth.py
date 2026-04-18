"""Auth-related Pydantic schemas (STEPS.md Phase 3)."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class BusinessSummary(BaseModel):
    """A business the user can administer."""

    id: str
    name: str
    slug: str
    role: str


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    is_super_admin: bool = False
    businesses: list[BusinessSummary] = Field(default_factory=list)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    session: TokenPair
    user: UserProfile


class SignupResponse(BaseModel):
    user: UserProfile
    session: TokenPair | None = None
    message: str | None = None


class LogoutResponse(BaseModel):
    ok: bool = True
    message: str = "Signed out."
