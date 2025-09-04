import pytest
import tempfile
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import schemas
from operations import book_operations


def test_create_book_endpoint(client: TestClient, auth_header):
    """
    Testcase creating a book.
    """
    response = client.post(
        "/books/",
        json={
            "title": "Python",
            "author": "Imran",
            "description": "complete tasks of python",
        },
        headers=auth_header,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == "Python"
    assert "id" in data


def test_get_books_endpoint(client: TestClient, auth_header):
    """
    Testcase retrieving all books.
    """
    response = client.get("/books/", headers=auth_header)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)


@pytest.fixture
def create_test_book(db_session: Session, test_user):
    """
    Fixture to create a book using book_operations.

    Args:
        db_session (Session): SQLAlchemy session.
        test_user: Test user object.

    Returns:
        Book: Created book object.
    """
    book_data = schemas.BookCreate(
        title="Python",
        author="Imran",
        description="Implement Tasks",
    )
    return book_operations.create_book(db_session, book_data, test_user.id)


def test_get_book_endpoint(client: TestClient, auth_header, create_test_book):
    """
    Testcase retrieving a single book by ID.
    """
    response = client.get(f"/books/{create_test_book.id}", headers=auth_header)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == create_test_book.id
    assert "avg_rating" in data


def test_update_book_endpoint(
        client: TestClient,
        auth_header,
        create_test_book
        ):
    """
    Testcase updating a book.
    """
    response = client.put(
        f"/books/{create_test_book.id}",
        json={"title": "Python Updated Book"},
        headers=auth_header,
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["title"] == "Python Updated Book"


def test_delete_book_endpoint(
        client: TestClient,
        auth_header, create_test_book
        ):
    """
    Testcase deleting a book.
    """
    response = client.delete(
        f"/books/{create_test_book.id}",
        headers=auth_header
        )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == create_test_book.id


def test_upload_cover_image_endpoint(
        client: TestClient,
        auth_header,
        create_test_book
        ):
    """
    Testcase uploading a cover image.
    """
    with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
        tmp.write(b"image content")
        tmp.seek(0)
        files = {"file": ("cover.jpg", tmp, "image/jpeg")}
        response = client.post(
            f"/books/{create_test_book.id}/cover",
            files=files,
            headers=auth_header,
        )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "cover_image" in data
    assert "/uploads/" in data["cover_image"]


def test_create_book_operation(db_session: Session, test_user):
    """
    Testcase creating a book.
    """
    book_data = schemas.BookCreate(
        title="Java",
        author="Ali",
        description="Java Tutorial",
    )
    book = book_operations.create_book(db_session, book_data, test_user.id)
    assert book.title == "Java"
    assert book.owner_id == test_user.id


def test_get_book_by_id_operation(
        db_session: Session,
        create_test_book):
    """
    Testcase retrieving a book by ID.
    """
    book = book_operations.get_book_by_id(db_session, create_test_book.id)
    assert book.id == create_test_book.id
    assert book.title == create_test_book.title


def test_update_book_info_operation(
        db_session: Session,
        create_test_book,
        test_user
        ):
    """
    Testcase updating book information.
    """
    update_data = schemas.BookUpdate(title="Java Updated")
    updated_book = book_operations.update_book_info(
        db_session, create_test_book.id, update_data, test_user
    )
    assert updated_book.title == "Java Updated"


def test_delete_book_record_operation(
        db_session: Session,
        create_test_book,
        test_user
        ):
    """
    Testcase deleting a book.
    """
    deleted_book = book_operations.delete_book_record(
        db_session,
        create_test_book.id,
        test_user
    )
    assert deleted_book.id == create_test_book.id
    assert book_operations.get_book_by_id(
        db_session,
        create_test_book.id
        ) is None
