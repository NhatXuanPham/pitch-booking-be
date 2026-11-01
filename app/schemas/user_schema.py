from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enum import Gender, UserRole
from app.utils.validators import (
    normalize_gender,
    sanitize_text,
    strip_empty_string,
    validate_avatar_url,
    validate_date_not_in_future,
    validate_phone_number,
)


class BaseUserResponse(BaseModel):
    model_config = {"from_attributes": True}

    @field_validator("gender", mode="before", check_fields=False)
    @classmethod
    def parse_gender(cls, v: Any) -> Any:
        return normalize_gender(v)


class PublicUserResponse(BaseUserResponse):
    id: int
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    gender: Optional[Gender] = None
    bio: Optional[str] = None
    created_at: Optional[datetime] = None


class UserResponse(BaseUserResponse):
    id: int
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool = True
    is_email_verified: bool = False
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    avatar_url: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    bio: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MeResponse(UserResponse):
    pass


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=500)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    bio: Optional[str] = Field(None, max_length=1000)

    @field_validator("full_name", "address", "bio", mode="before")
    @classmethod
    def sanitize_user_inputs(cls, v: Any) -> Any:
        return sanitize_text(v)

    @field_validator("phone_number", "avatar_url", mode="before")
    @classmethod
    def strip_empty_strings(cls, v: Any) -> Any:
        return strip_empty_string(v)

    @field_validator("gender", mode="before")
    @classmethod
    def validate_gender(cls, v: Any) -> Any:
        return normalize_gender(v)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str | None) -> str | None:
        return validate_phone_number(v)

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v: str | None) -> str | None:
        return validate_avatar_url(v)

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, v: date | None) -> date | None:
        return validate_date_not_in_future(v, field_name="date_of_birth")
