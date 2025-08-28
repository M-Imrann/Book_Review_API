import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app import models, security

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    bind=engine, autoflush=False, expire_on_commit=False
)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """
    Creates all tables before tests and drops them after tests.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test.db"):
        os.remove("test.db")


@pytest.fixture
def db():
    """
    Provide a database session for tests.

    Closes the session after use.
    """
    db_session = TestingSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


def override_get_db():
    """
    Dependency override for FastAPI routes to use test database.
    """
    db_session = TestingSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestAuth:
    """
    TestAuth class for user authentication endpoints.
    """

    def test_register_user(self):
        """
        Testcase for creating a new user.
        """
        resp = client.post(
            "/register",
            json={"email": "test@example.com", "password": "secret"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert data["role"] == "user"

    def test_register_duplicate_email(self):
        """
        Testcase for registering a user with an existing email.
        """
        resp = client.post(
            "/register",
            json={"email": "test@example.com", "password": "another"},
        )
        assert resp.status_code == 400

    def test_login_user(self):
        """
        Testcase for logging in with correct credentials.
        """
        resp = client.post(
            "/login",
            data={"username": "test@example.com", "password": "secret"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        self.token = data["access_token"]

    def test_login_wrong_password(self):
        """
        Testcase for logging in with incorrect password.
        """
        resp = client.post(
            "/login",
            data={"username": "test@example.com", "password": "wrong"},
        )
        assert resp.status_code == 400


class TestAdmin:
    """
    TestAdmin class for admin-related endpoints.
    """

    def setup_method(self):
        """
        Login user and set headers for authorization.
        """
        resp = client.post(
            "/login",
            data={"username": "test@example.com", "password": "secret"},
        )
        self.token = resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_promote_user(self):
        """
        Testcase promoting a regular user to admin.
        """
        resp = client.post(
            "/register",
            json={"email": "promote@example.com", "password": "secret"},
        )
        assert resp.status_code == 200
        user_id = resp.json()["id"]

        db = next(override_get_db())
        admin_user = db.query(models.User).filter(models.User.email ==
                                                  "test@example.com").first()
        admin_user.role = "admin"
        db.commit()

        resp = client.post(f"/admin/promote/{user_id}", headers=self.headers)
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"


class TestBooks:
    """
    Testbooks class for book-related endpoints.
    """

    def setup_method(self):
        """
        Login user and set headers for authorization.
        """
        resp = client.post(
            "/login",
            data={"username": "test@example.com", "password": "secret"},
        )
        self.token = resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_create_book(self):
        """
        Testcase for creating a new book.
        """
        resp = client.post(
            "/books/",
            headers=self.headers,
            json={
                "title": "Book One",
                "author": "Author A",
                "description": "Desc"
                },
        )
        assert resp.status_code == 200
        self.book_id = resp.json()["id"]

    def test_get_books(self):
        """
        Testcase for retrieving all books.
        """
        resp = client.get("/books/", headers=self.headers)
        assert resp.status_code == 200
        books = resp.json()
        assert isinstance(books, list)
        assert books[0]["title"] == "Book One"

    def test_get_book_by_id(self):
        """
        Testcase for retrieving a book by its ID.
        """
        resp = client.get("/books/1", headers=self.headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Book One"

    def test_update_book(self):
        """
        Testcase for updating a book's title.
        """
        resp = client.put(
            "/books/1",
            headers=self.headers,
            json={"title": "Updated Title"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    def test_delete_book(self):
        """
        Testcase for deleting a book.
        """
        resp = client.post(
            "/books/",
            headers=self.headers,
            json={
                "title": "DeleteMe",
                "author": "Auth",
                "description": "Temp"
                },
        )
        bid = resp.json()["id"]
        resp = client.delete(f"/books/{bid}", headers=self.headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == bid

    def test_book_not_found(self):
        """
        Testcase for retrieving a non-existing book.
        """
        resp = client.get("/books/999", headers=self.headers)
        assert resp.status_code == 404


class TestReviews:
    """
    TestReviews Class for review-related endpoints.
    """

    def setup_method(self):
        """
        Login user, create a book for reviews, and set headers.
        """
        resp = client.post(
            "/login",
            data={"username": "test@example.com", "password": "secret"},
        )
        self.token = resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        client.post(
            "/books/",
            headers=self.headers,
            json={"title": "ReviewBook", "author": "X", "description": "Y"},
        )

    def test_create_review(self):
        """
        Testcase for creating a new review for a book.
        """
        resp = client.post(
            "/books/reviews/",
            headers=self.headers,
            json={"book_id": 1, "content": "Nice", "rating": 5},
        )
        assert resp.status_code == 200
        self.review_id = resp.json()["id"]
        assert resp.json()["rating"] == 5

    def test_get_reviews(self):
        """
        Testcase for retrieving reviews for a book.
        """
        resp = client.get("/books/1/reviews", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["rating"] == 5

    def test_update_review(self):
        """
        Testcase for updating review content.
        """
        resp = client.put(
            "/books/reviews/1",
            headers=self.headers,
            json={"content": "Updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "Updated"

    def test_delete_review(self):
        """
        Testcase for deleting a review.
        """
        resp = client.delete("/books/reviews/1", headers=self.headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == 1

    def test_review_not_found(self):
        """
        Testcase for updating a non-existing review.
        """
        resp = client.put(
            "/books/reviews/999",
            headers=self.headers,
            json={"content": "x"},
        )
        assert resp.status_code == 404


class TestReactions:
    """
    TestReaction Class for reaction endpoints for reviews.
    """

    def setup_method(self):
        """
        Login user, create book and review for reactions, and set headers.
        """
        resp = client.post(
            "/login",
            data={"username": "test@example.com", "password": "secret"},
        )
        self.token = resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        client.post(
            "/books/",
            headers=self.headers,
            json={"title": "RBook", "author": "B", "description": "C"},
        )
        client.post(
            "/books/reviews/",
            headers=self.headers,
            json={"book_id": 1, "content": "react me", "rating": 4},
        )

    def test_react_create_like(self):
        """
        Testcase for creating a like reaction.
        """
        resp = client.post(
            "/books/reviews/react",
            headers=self.headers,
            json={"review_id": 1, "value": 1},
        )
        assert resp.status_code == 200
        assert resp.json()["action"] == "created"

    def test_react_update_dislike(self):
        """
        Testcase for changing reaction from like to dislike.
        """
        client.post(
            "/books/reviews/react",
            headers=self.headers,
            json={"review_id": 1, "value": 1},
        )
        resp = client.post(
            "/books/reviews/react",
            headers=self.headers,
            json={"review_id": 1, "value": -1},
        )
        assert resp.status_code == 200
        assert resp.json()["action"] in ("created", "updated")

    def test_react_remove(self):
        """
        Testcase for removing a reaction by clicking same value again.
        """
        client.post(
            "/books/reviews/react",
            headers=self.headers,
            json={"review_id": 1, "value": 1},
        )
        resp = client.post(
            "/books/reviews/react",
            headers=self.headers,
            json={"review_id": 1, "value": 1},
        )
        assert resp.status_code == 200
        assert resp.json()["action"] == "removed"

    def test_invalid_reaction_value(self):
        """
        Testcase for invalid reaction value raises error.
        """
        with pytest.raises(ValueError) as exc:
            client.post(
                "/books/reviews/react",
                headers=self.headers,
                json={"review_id": 1, "value": 5},
            )
        assert "Reaction value must be 1 (like) or -1 (dislike)"\
            in str(exc.value)


class TestSecurity:
    """
    TestSecurity class for security-related functions.
    """

    def test_password_hashing_and_verify(self):
        """
        Testcase for hashing a password and verifying it.
        """
        pw = "mypassword"
        hashed = security.get_password_hash(pw)
        assert security.verify_password(pw, hashed)

    def test_create_access_token_and_decode(self):
        """
        Testcase for creating an access token and decoding it.
        """
        token = security.create_access_token({"sub": "123"})
        decoded = security.jwt.decode(token, security.SECRET_KEY,
                                      algorithms=[security.ALGORITHM])
        assert decoded["sub"] == "123"
