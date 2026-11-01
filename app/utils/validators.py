from datetime import date
import re
from typing import Any

from app.models.enum import Gender


def normalize_gender(v: Any) -> Any:
    """
    Normalize gender string to Gender enum, or return None / original value.
    Supports case-insensitive string parsing (e.g. 'male' -> Gender.MALE).
    """
    if v is None:
        return None
    if isinstance(v, str):
        cleaned = v.strip().upper()
        if not cleaned:
            return None
        if cleaned in Gender.__members__:
            return Gender[cleaned]
        return cleaned
    return v


def strip_empty_string(v: Any) -> Any:
    """
    Strip leading/trailing whitespace and convert empty strings to None.
    Non-string values are returned as-is.
    """
    if isinstance(v, str):
        v = v.strip()
        return v if v else None
    return v


def validate_phone_number(v: str | None) -> str | None:
    """
    Clean and validate phone number (removes spaces, dashes, parens, dots).
    Must contain 7 to 15 digits.
    """
    if v is None:
        return None
    cleaned = re.sub(r"[\s\-\(\)\.]", "", v)
    if not re.match(r"^\+?[0-9]{7,15}$", cleaned):
        raise ValueError("Invalid phone number (must contain 7 to 15 digits)")
    return cleaned


def validate_avatar_url(v: str | None) -> str | None:
    """
    Validate that avatar_url is a valid HTTP(S) URL.
    """
    if v is None:
        return None
    if not re.match(r"^https?://\S+$", v, flags=re.IGNORECASE):
        raise ValueError("avatar_url must be an http(s) URL")
    return v


def validate_date_not_in_future(v: date | None, field_name: str = "date_of_birth") -> date | None:
    """
    Ensure a date value is not in the future.
    """
    if v is not None and v > date.today():
        raise ValueError(f"{field_name} cannot be in the future")
    return v
