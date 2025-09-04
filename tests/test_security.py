import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock
import time
from app import security


def test_password_hashing_and_verification():
    """
    Testcase password hashing and verification.
    """
    plain_password = "mypassword"
    hashed_password = security.get_password_hash(plain_password)

    # Verify correct password
    assert security.verify_password(plain_password, hashed_password)

    # Verify incorrect password fails
    assert not security.verify_password("wrongpass", hashed_password)


def test_create_access_token_and_decode():
    """
    Testcase creating a JWT access token and decoding it.
    """
    data = {"sub": "1"}
    token = security.create_access_token(data)
    decoded = security.jwt.decode(
        token, security.SECRET_KEY, algorithms=[security.ALGORITHM]
    )

    assert decoded["sub"] == "1"
    assert "exp" in decoded


def test_get_current_user_success(monkeypatch, test_user):
    """
    Testcase get_current_user returns correct user when JWT is valid.
    """
    # Patch jwt.decode to return a valid payload
    monkeypatch.setattr(
        security.jwt,
        "decode",
        lambda token, key, algorithms: {"sub": str(test_user.id)}
    )

    class MockQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return test_user

    mock_db = MagicMock()
    mock_db.query.return_value = MockQuery()

    user = security.get_current_user(token="fake", db_session=mock_db)
    assert user.id == test_user.id


def test_get_current_user_invalid_token(monkeypatch):
    """
    Testcase get_current_user raises HTTPException on invalid token.
    """
    monkeypatch.setattr(
        security.jwt,
        "decode",
        lambda *a, **k: (_ for _ in ()).throw(security.jwt.JWTError())
    )

    with pytest.raises(HTTPException) as exc:
        security.get_current_user(token="invalid", db_session=MagicMock())

    assert exc.value.status_code == 401


def test_require_admin_with_admin(test_admin):
    """
    Testcase require_admin allows admin user.
    """
    user = security.require_admin(current_user=test_admin)
    assert user.id == test_admin.id


def test_require_admin_with_non_admin(test_user):
    """
    Testcase require_admin blocks non-admin user.
    """
    with pytest.raises(HTTPException) as exc:
        security.require_admin(current_user=test_user)

    assert exc.value.status_code == 403


def test_rate_limit_allows_requests():
    """
    Testcase rate_limit allows requests under limit.
    """
    security._request_timestamps.clear()
    request = MagicMock()
    request.client.host = "127.0.0.1"

    user = MagicMock()
    user.id = 1

    for limit in range(5):
        security.rate_limit(request, current_user=user)

    assert len(security._request_timestamps[f"user:{user.id}"]) == 5


def test_rate_limit_exceeded():
    """
    Testcase rate_limit raises HTTPException when limit exceeded.
    """
    security._request_timestamps.clear()
    request = MagicMock()
    request.client.host = "127.0.0.1"

    user = MagicMock()
    user.id = 2

    now = time.time()
    security._request_timestamps[f"user:{user.id}"] = [now]\
        * security._MAX_REQUESTS_PER_WINDOW

    with pytest.raises(HTTPException) as exc:
        security.rate_limit(request, current_user=user)

    assert exc.value.status_code == 429
