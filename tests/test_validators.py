from datetime import date, timedelta
import pytest
from app.utils.validators import (
    normalize_gender,
    sanitize_text,
    strip_empty_string,
    validate_avatar_url,
    validate_date_not_in_future,
    validate_phone_number,
)
from app.models.enum import Gender


def test_sanitize_text_escapes_xss():
    xss_payload = '<script>alert("XSS")</script>'
    sanitized = sanitize_text(xss_payload)
    assert sanitized == "&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;"


def test_sanitize_text_handles_html_tags():
    payload = '<img src=x onerror=alert(1)>'
    sanitized = sanitize_text(payload)
    assert "<" not in sanitized
    assert ">" not in sanitized
    assert sanitized == "&lt;img src=x onerror=alert(1)&gt;"


def test_sanitize_text_trims_and_empties():
    assert sanitize_text("   Hello World   ") == "Hello World"
    assert sanitize_text("   ") is None
    assert sanitize_text(None) is None


def test_strip_empty_string():
    assert strip_empty_string("  abc  ") == "abc"
    assert strip_empty_string("   ") is None
    assert strip_empty_string(None) is None


def test_normalize_gender():
    assert normalize_gender("male") == Gender.MALE
    assert normalize_gender("FEMALE") == Gender.FEMALE
    assert normalize_gender("OTHER") == Gender.OTHER
    assert normalize_gender(None) is None
    assert normalize_gender("   ") is None
    assert normalize_gender("invalid") == "INVALID"


def test_validate_avatar_url():
    assert validate_avatar_url("https://example.com/avatar.jpg") == "https://example.com/avatar.jpg"
    assert validate_avatar_url("http://example.com/pic.png") == "http://example.com/pic.png"
    assert validate_avatar_url(None) is None

    with pytest.raises(ValueError, match="avatar_url must be an http"):
        validate_avatar_url("javascript:alert(1)")

    with pytest.raises(ValueError, match="avatar_url must be an http"):
        validate_avatar_url("data:text/html;base64,PHNjcmlwdD4=")


def test_validate_phone_number():
    assert validate_phone_number("+84 (912) 345-678") == "+84912345678"
    assert validate_phone_number("0912345678") == "0912345678"
    assert validate_phone_number(None) is None

    with pytest.raises(ValueError, match="Invalid phone number"):
        validate_phone_number("abc")


def test_validate_date_not_in_future():
    past_date = date.today() - timedelta(days=100)
    assert validate_date_not_in_future(past_date) == past_date
    assert validate_date_not_in_future(date.today()) == date.today()
    assert validate_date_not_in_future(None) is None

    future_date = date.today() + timedelta(days=1)
    with pytest.raises(ValueError, match="cannot be in the future"):
        validate_date_not_in_future(future_date)
