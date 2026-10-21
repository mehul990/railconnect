from fastapi.testclient import TestClient
from app.config import settings


def test_user_registration_success(client: TestClient):
    """Test standard user account registration."""
    resp = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "SecurePassword123",
            "full_name": "Test User",
            "role": "passenger"
        }
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "Test User"
    assert data["role"] == "passenger"
    assert data["is_active"] is True
    assert "hashed_password" not in data


def test_duplicate_registration_fails(client: TestClient):
    """Test that attempting to register an existing email returns 400."""
    resp = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "aarav@example.com",
            "password": "AnotherPassword123",
            "full_name": "Duplicate Aarav",
            "role": "passenger"
        }
    )
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"]


def test_login_success(client: TestClient):
    """Test logging in with valid credentials returns JWT token."""
    resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": "aarav@example.com", "password": "Password@123"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "passenger"


def test_login_invalid_password(client: TestClient):
    """Test login with incorrect password returns 401."""
    resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": "aarav@example.com", "password": "WrongPassword"}
    )
    assert resp.status_code == 401
    assert "Invalid email or password" in resp.json()["detail"]


def test_login_nonexistent_email(client: TestClient):
    """Test login with non-existent email returns 401."""
    resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": "nobody@example.com", "password": "AnyPassword"}
    )
    assert resp.status_code == 401


def test_unauthorized_access_protected_endpoint(client: TestClient):
    """Test that requesting protected route without token returns 401."""
    resp = client.get(f"{settings.API_V1_STR}/auth/me")
    assert resp.status_code == 401


def test_get_profile_success(client: TestClient, passenger_token: str):
    """Test fetching own profile with valid JWT."""
    resp = client.get(
        f"{settings.API_V1_STR}/auth/me",
        headers={"Authorization": f"Bearer {passenger_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "aarav@example.com"
    assert data["full_name"] == "Aarav Sharma"


def test_logout_token_revocation(client: TestClient, passenger_token: str):
    """Test that logout revokes token and subsequent requests with the same token fail."""
    # Verify token works initially
    resp1 = client.get(
        f"{settings.API_V1_STR}/auth/me",
        headers={"Authorization": f"Bearer {passenger_token}"}
    )
    assert resp1.status_code == 200

    # Perform logout
    resp_logout = client.post(
        f"{settings.API_V1_STR}/auth/logout",
        headers={"Authorization": f"Bearer {passenger_token}"}
    )
    assert resp_logout.status_code == 200
    assert "revoked" in resp_logout.json()["message"]

    # Subsequent access with same token must be rejected
    resp2 = client.get(
        f"{settings.API_V1_STR}/auth/me",
        headers={"Authorization": f"Bearer {passenger_token}"}
    )
    assert resp2.status_code == 401
    assert "revoked" in resp2.json()["detail"]


def test_forgot_and_reset_password_flow(client: TestClient):
    """Test complete forgot-password and reset-password cycle."""
    # 1. Request forgot password
    resp1 = client.post(
        f"{settings.API_V1_STR}/auth/forgot-password",
        json={"email": "aarav@example.com"}
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    reset_token = data1["dev_reset_token"]
    assert reset_token is not None

    # 2. Reset password with valid token
    resp2 = client.post(
        f"{settings.API_V1_STR}/auth/reset-password",
        json={"token": reset_token, "new_password": "NewSecretPassword123"}
    )
    assert resp2.status_code == 200
    assert "successfully updated" in resp2.json()["message"]

    # 3. Old password should now fail
    resp_old = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": "aarav@example.com", "password": "Password@123"}
    )
    assert resp_old.status_code == 401

    # 4. New password should succeed
    resp_new = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": "aarav@example.com", "password": "NewSecretPassword123"}
    )
    assert resp_new.status_code == 200

    # 5. Token cannot be reused (single-use check)
    resp3 = client.post(
        f"{settings.API_V1_STR}/auth/reset-password",
        json={"token": reset_token, "new_password": "AnotherPassword456"}
    )
    assert resp3.status_code == 400
    assert "already been used" in resp3.json()["detail"]
