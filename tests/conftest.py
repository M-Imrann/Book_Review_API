import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app import schemas
from operations import auth_operations


SQLALCHEMY_TEST_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False}
    )
TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False
    )


def override_get_db():
    """
    Override FastAPI's get_db dependency with
    test database session.
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """
    Create and drop tables for the test database.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """
    Fixture for FastAPI TestClient.
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture
def db_session():
    """
    Fixture for direct access to a database session.
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    """
    Create a test user.
    """
    email = f"user_{uuid.uuid4().hex}@example.com"
    user_data = schemas.UserCreate(
        email=email,
        password="pass123",
        role="user"
        )
    return auth_operations.create_user(db_session, user_data)


@pytest.fixture
def test_admin(db_session):
    """
    Create a test admin user.
    """
    email = f"admin_{uuid.uuid4().hex}@example.com"
    admin_data = schemas.UserCreate(
        email=email,
        password="pass123",
        role="admin"
        )
    return auth_operations.create_user(db_session, admin_data)


@pytest.fixture
def auth_header(client, test_user):
    """
    Return authorization header for the test user.
    """
    response = client.post(
        "/auth/login",
        data={"username": test_user.email, "password": "pass123"}
        )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_header(client, test_admin):
    """
    Return authorization header for the admin user.
    """
    response = client.post(
        "/auth/login",
        data={"username": test_admin.email, "password": "pass123"}
        )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
