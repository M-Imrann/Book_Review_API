import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import schemas
from operations import review_operations, book_operations


@pytest.fixture
def create_test_book_for_review(db_session: Session, test_user):
    """
    Create a test book for review.
    """
    book_data = schemas.BookCreate(
        title="Ruby",
        author="Nasir",
        description="Ruby Book"
    )
    return book_operations.create_book(db_session, book_data, test_user.id)


@pytest.fixture
def create_test_review(
        db_session: Session,
        test_user,
        create_test_book_for_review
        ):
    """
    Create a test review for a book.
    """
    review_data = schemas.ReviewCreate(
        content="Great book!",
        rating=5,
        book_id=create_test_book_for_review.id
    )
    return review_operations.create_review_with_counts(
        db_session,
        review_data,
        test_user.id
        )


def test_create_review_endpoint(
        client: TestClient,
        auth_header,
        create_test_book_for_review):
    """
    Testcase creating a review via API.
    """
    payload = {
        "content": "Great book!",
        "rating": 5,
        "book_id": create_test_book_for_review.id
    }
    response = client.post(
        "/books/reviews/",
        json=payload,
        headers=auth_header
        )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["content"] == "Great book!"
    assert "likes" in data and "dislikes" in data


def test_get_reviews_endpoint(
        client: TestClient,
        auth_header,
        create_test_review
        ):
    """
    Testcase retrieving reviews for a book via API.
    """
    response = client.get(
        f"/books/{create_test_review.book_id}/reviews",
        headers=auth_header
        )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert any(review["id"] == create_test_review.id for review in data)


def test_update_review_endpoint(
        client: TestClient,
        auth_header,
        create_test_review
        ):
    """
    Testcase updating a review via API.
    """
    payload = {"content": "Great book!", "rating": 5}
    response = client.put(
        f"/books/reviews/{create_test_review.id}",
        json=payload,
        headers=auth_header
        )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["content"] == "Great book!"


def test_delete_review_endpoint(
        client: TestClient,
        auth_header,
        create_test_review
        ):
    """
    Testcase deleting a review via API.
    """
    response = client.delete(
        f"/books/reviews/{create_test_review.id}",
        headers=auth_header
        )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == create_test_review.id


def test_react_to_review_endpoint(
        client: TestClient,
        auth_header,
        create_test_review
        ):
    """
    Testcase reacting to a review via API.
    """
    payload = {"review_id": create_test_review.id, "value": 1}
    response = client.post(
        "/books/reviews/react",
        json=payload,
        headers=auth_header
        )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["action"] in ["created", "updated"]


def test_create_review(
        db_session: Session,
        test_user,
        create_test_book_for_review
        ):
    """
    Testcase creating a review.
    """
    review = review_operations.create_review_with_counts(
        db_session,
        schemas.ReviewCreate(
            content="Great book!",
            rating=5,
            book_id=create_test_book_for_review.id
        ),
        test_user.id
    )
    assert review.content == "Great book!"
    assert review.user_id == test_user.id
    assert hasattr(review, "likes") and hasattr(review, "dislikes")


def test_get_reviews_for_book(db_session: Session, create_test_review):
    """
    Testcase retrieving reviews for a book.
    """
    reviews = review_operations.get_reviews_for_book_with_counts(
        db_session,
        create_test_review.book_id
        )
    assert len(reviews) > 0
    assert reviews[0].id == create_test_review.id


def test_update_review(
        db_session: Session,
        create_test_review,
        test_user
        ):
    """
    Testcase updating a review.
    """
    updated = review_operations.update_review_with_counts(
        db_session,
        create_test_review.id,
        schemas.ReviewUpdate(content="Great book!", rating=5),
        test_user
    )
    assert updated.content == "Great book!"


def test_delete_review(
        db_session: Session,
        create_test_review,
        test_user
        ):
    """
    Testcase deleting a review.
    """
    deleted = review_operations.delete_review_with_counts(
        db_session,
        create_test_review.id,
        test_user
        )
    assert deleted.id == create_test_review.id
    assert review_operations.get_review_by_id(
        db_session,
        create_test_review.id
        ) is None


def test_react_to_review(
        db_session: Session,
        create_test_review,
        test_user
        ):
    """
    Testcase reacting to a review.
    """
    result = review_operations.react_to_review(
        db_session, create_test_review.id, test_user.id, 1
    )
    assert result["action"] in ["created", "updated"]
    counts = review_operations.get_review_likes_dislikes(
        db_session,
        create_test_review.id
        )
    assert "likes" in counts and "dislikes" in counts
