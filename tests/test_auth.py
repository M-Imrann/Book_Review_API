from fastapi import status


def test_register_user_success(client):
    """
    Test successful user registration.

    Sends a POST request to the /auth/register endpoint with
    a new user's email, password, and role, and verifies that
    the user is created successfully.
    """
    response = client.post("/auth/register", json={
        "email": "ali@example.com",
        "password": "password123",
        "role": "user"
    })

    # Verify response status code and returned data
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "ali@example.com"
    assert data["role"] == "user"
    assert "id" in data


def test_register_user_existing_email(client):
    """
    Test registration with an already existing email.
    """

    # Attempt to register the same email again
    response = client.post("/auth/register", json={
        "email": "ali@example.com",
        "password": "password123",
        "role": "user"
    })

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Email already registered"


def test_login_user_success(client):
    """
    Test successful user login.

    Sends a POST request to /auth/login
    with the user's credentials.
    Verifies that an access token is returned along with the correct
    token type.
    """
    # Attempt to login
    response = client.post("/auth/login", data={
        "username": "ali@example.com",
        "password": "password123"
    })

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
