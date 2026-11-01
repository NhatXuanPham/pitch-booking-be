import uuid
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services import auth_service as auth_service_module
from app.services.email_service import email_service

FIXED_OTP = "246810"
PASSWORD = "Sup3rSecret!pass"


@pytest.fixture(autouse=True)
def _mock_email_and_otp(monkeypatch):
    monkeypatch.setattr(email_service, "send_registration_otp_email", AsyncMock())
    monkeypatch.setattr(email_service, "send_password_reset_otp_email", AsyncMock())
    monkeypatch.setattr(auth_service_module, "generate_otp", lambda: FIXED_OTP)


@pytest_asyncio.fixture
async def authenticated_user(async_client: AsyncClient):
    suffix = uuid.uuid4().hex[:10]
    identity = {
        "email": f"user_{suffix}@example.com",
        "username": f"user_{suffix}",
        "password": PASSWORD,
    }

    # Send OTP & Register
    await async_client.post(
        "/api/v1/auth/send-otp",
        json={"email": identity["email"], "purpose": "REGISTER"},
    )
    reg_resp = await async_client.post(
        "/api/v1/auth/register",
        json={**identity, "otp": FIXED_OTP},
    )
    assert reg_resp.status_code == 201
    tokens = reg_resp.json()["tokens"]
    token = tokens["access_token"]

    yield {"identity": identity, "token": token, "auth_headers": {"Authorization": f"Bearer {token}"}}

    async with AsyncSessionLocal() as session:
        await session.execute(delete(User).where(User.email == identity["email"]))
        await session.commit()


@pytest.mark.asyncio
async def test_get_me_initial_profile(async_client: AsyncClient, authenticated_user):
    headers = authenticated_user["auth_headers"]
    response = await async_client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == authenticated_user["identity"]["email"]
    assert data["username"] == authenticated_user["identity"]["username"]
    assert data["full_name"] is None
    assert data["phone_number"] is None
    assert data["address"] is None


@pytest.mark.asyncio
async def test_update_me_all_fields(async_client: AsyncClient, authenticated_user):
    headers = authenticated_user["auth_headers"]
    update_payload = {
        "full_name": "Nguyễn Văn A",
        "phone_number": "0912345678",
        "address": "123 Đường Số 1, Quận 1, TP. HCM",
        "avatar_url": "https://example.com/avatar.jpg",
        "date_of_birth": "1995-10-25",
        "gender": "male",
        "bio": "Đam mê bóng đá sân 7 và cầu lông",
    }
    response = await async_client.patch("/api/v1/users/me", json=update_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == update_payload["full_name"]
    assert data["phone_number"] == update_payload["phone_number"]
    assert data["address"] == update_payload["address"]
    assert data["avatar_url"] == update_payload["avatar_url"]
    assert data["date_of_birth"] == update_payload["date_of_birth"]
    assert data["gender"] == "MALE"
    assert data["bio"] == update_payload["bio"]

    # Verify persistence via GET /me
    get_resp = await async_client.get("/api/v1/users/me", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["full_name"] == "Nguyễn Văn A"
    assert get_resp.json()["phone_number"] == "0912345678"
    assert get_resp.json()["gender"] == "MALE"



@pytest.mark.asyncio
async def test_partial_update_keeps_existing_fields(async_client: AsyncClient, authenticated_user):
    headers = authenticated_user["auth_headers"]

    # Step 1: Set full_name and phone_number
    await async_client.patch(
        "/api/v1/users/me",
        json={"full_name": "Tran Van B", "phone_number": "0987654321"},
        headers=headers,
    )

    # Step 2: Update only bio
    resp = await async_client.patch(
        "/api/v1/users/me",
        json={"bio": "Hậu vệ thòng"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Tran Van B"
    assert data["phone_number"] == "0987654321"
    assert data["bio"] == "Hậu vệ thòng"


@pytest.mark.asyncio
async def test_update_invalid_phone_number(async_client: AsyncClient, authenticated_user):
    headers = authenticated_user["auth_headers"]
    response = await async_client.patch(
        "/api/v1/users/me",
        json={"phone_number": "not-a-phone"},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_user_by_id(async_client: AsyncClient, authenticated_user):
    headers = authenticated_user["auth_headers"]
    me_resp = await async_client.get("/api/v1/users/me", headers=headers)
    user_id = me_resp.json()["id"]

    # Fetch user profile by ID (public view)
    profile_resp = await async_client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert profile_resp.status_code == 200
    public_data = profile_resp.json()
    assert public_data["id"] == user_id
    assert public_data["username"] == authenticated_user["identity"]["username"]
    assert "gender" in public_data
    assert public_data["gender"] is None
    # Sensitive PII must not be exposed to other users
    assert "email" not in public_data
    assert "phone_number" not in public_data
    assert "address" not in public_data
    assert "date_of_birth" not in public_data
    assert "is_email_verified" not in public_data

    # Update gender and verify GET by ID returns updated gender
    await async_client.patch(
        "/api/v1/users/me",
        json={"gender": "FEMALE"},
        headers=headers,
    )
    updated_profile_resp = await async_client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert updated_profile_resp.status_code == 200
    assert updated_profile_resp.json()["gender"] == "FEMALE"


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(async_client: AsyncClient, authenticated_user):
    headers = authenticated_user["auth_headers"]
    response = await async_client.get("/api/v1/users/99999999", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unauthorized_user_endpoints(async_client: AsyncClient):
    resp_get = await async_client.get("/api/v1/users/me")
    assert resp_get.status_code == 401

    resp_patch = await async_client.patch("/api/v1/users/me", json={"full_name": "Test"})
    assert resp_patch.status_code == 401


@pytest.mark.asyncio
async def test_get_me_disabled_user(async_client: AsyncClient, authenticated_user):
    from sqlalchemy import update

    headers = authenticated_user["auth_headers"]
    email = authenticated_user["identity"]["email"]

    # Disable user in DB
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.email == email).values(is_active=False))
        await session.commit()

    resp = await async_client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Account has been disabled"

    resp_patch = await async_client.patch(
        "/api/v1/users/me", json={"full_name": "Test"}, headers=headers
    )
    assert resp_patch.status_code == 403
    assert resp_patch.json()["detail"] == "Account has been disabled"


@pytest.mark.asyncio
async def test_update_phone_number_cleaned(async_client: AsyncClient, authenticated_user):
    headers = authenticated_user["auth_headers"]
    resp = await async_client.patch(
        "/api/v1/users/me",
        json={"phone_number": "+84 (912) 345-678"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["phone_number"] == "+84912345678"


@pytest.mark.asyncio
async def test_update_invalid_avatar_url(async_client: AsyncClient, authenticated_user):
    headers = authenticated_user["auth_headers"]
    resp = await async_client.patch(
        "/api/v1/users/me",
        json={"avatar_url": "javascript:alert(1)"},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_future_date_of_birth(async_client: AsyncClient, authenticated_user):
    from datetime import date, timedelta

    headers = authenticated_user["auth_headers"]
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    resp = await async_client.patch(
        "/api/v1/users/me",
        json={"date_of_birth": tomorrow},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_invalid_gender(async_client: AsyncClient, authenticated_user):
    headers = authenticated_user["auth_headers"]
    resp = await async_client.patch(
        "/api/v1/users/me",
        json={"gender": "alien"},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_me_sanitizes_xss(async_client: AsyncClient, authenticated_user):
    headers = authenticated_user["auth_headers"]
    xss_payload = {
        "full_name": 'Hacker <script>alert("XSS")</script>',
        "bio": '<img src=x onerror=alert("hacked")> Yêu bóng đá',
        "address": '123 Đường Số 1 <iframe src="evil.com"></iframe>',
    }
    resp = await async_client.patch("/api/v1/users/me", json=xss_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Raw script, iframe, and img tags must be escaped
    assert "<script>" not in data["full_name"]
    assert "&lt;script&gt;" in data["full_name"]

    assert "<img" not in data["bio"]
    assert "&lt;img" in data["bio"]

    assert "<iframe" not in data["address"]
    assert "&lt;iframe" in data["address"]


@pytest.mark.asyncio
async def test_update_me_username_success(async_client: AsyncClient, authenticated_user):
    headers = authenticated_user["auth_headers"]
    new_username = "new_cool_username"
    resp = await async_client.patch(
        "/api/v1/users/me",
        json={"username": new_username},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == new_username

    # Re-sending the same username should succeed
    resp_same = await async_client.patch(
        "/api/v1/users/me",
        json={"username": new_username},
        headers=headers,
    )
    assert resp_same.status_code == 200
    assert resp_same.json()["username"] == new_username


@pytest.mark.asyncio
async def test_update_me_username_already_taken(async_client: AsyncClient, authenticated_user):
    from app.core.database import AsyncSessionLocal
    from app.models.user import User

    headers = authenticated_user["auth_headers"]
    taken_username = "another_existing_user"

    # Create another user in DB
    async with AsyncSessionLocal() as session:
        other_user = User(
            username=taken_username,
            email="other_unique_user@example.com",
            password_hash="fakehash",
        )
        session.add(other_user)
        await session.commit()

    resp = await async_client.patch(
        "/api/v1/users/me",
        json={"username": taken_username},
        headers=headers,
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Username is already taken"

    # Cleanup
    async with AsyncSessionLocal() as session:
        await session.delete(other_user)
        await session.commit()


@pytest.mark.asyncio
async def test_update_me_invalid_username_format(async_client: AsyncClient, authenticated_user):
    headers = authenticated_user["auth_headers"]

    # Invalid: contains @
    resp_at = await async_client.patch(
        "/api/v1/users/me",
        json={"username": "user@domain"},
        headers=headers,
    )
    assert resp_at.status_code == 422

    # Invalid: too short (< 6 chars)
    resp_short = await async_client.patch(
        "/api/v1/users/me",
        json={"username": "abcde"},
        headers=headers,
    )
    assert resp_short.status_code == 422

    # Invalid: contains spaces
    resp_spaces = await async_client.patch(
        "/api/v1/users/me",
        json={"username": "bad user"},
        headers=headers,
    )
    assert resp_spaces.status_code == 422



