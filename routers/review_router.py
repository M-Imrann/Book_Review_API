from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.security import get_current_user, rate_limit
from operations import review_operations
from typing import List


router = APIRouter(prefix="/books", tags=["reviews"])


@router.post(
    "/reviews/",
    response_model=schemas.Review,
    dependencies=[Depends(rate_limit)]
)
def create_review(
    review_data: schemas.ReviewCreate,
    db_session: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a review for a book by the current user.

    Args:
        review_data: The review content, rating, and book ID
        db_session: Database session for executing queries
        current_user: The authenticated user creating the review

    Returns:
        schemas.Review: The created review with like/dislike counts

    Raises:
        HTTPException: If the specified book does not exist
    """
    # Use the operation function that includes like/dislike counts
    return review_operations.create_review_with_counts(
        db_session,
        review_data,
        current_user.id
    )


@router.get(
    "/{book_id}/reviews",
    response_model=List[schemas.Review],
    dependencies=[Depends(rate_limit)]
)
def get_reviews(
    book_id: int,
    skip: int = 0,
    limit: int = 20,
    db_session: Session = Depends(get_db)
):
    """
    Get all reviews for a specific book, including likes/dislikes counts.

    Args:
        book_id: ID of the book to get reviews for
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        db_session: Database session for executing queries

    Returns:
        List[schemas.Review]: List of reviews with like/dislike counts
    """
    # Use the operation function that includes like/dislike counts
    return review_operations.get_reviews_for_book_with_counts(
        db_session,
        book_id,
        skip,
        limit
    )


@router.put(
    "/reviews/{review_id}",
    response_model=schemas.Review,
    dependencies=[Depends(rate_limit)]
)
def update_review(
    review_id: int,
    review_data: schemas.ReviewUpdate,
    db_session: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update a review.

    Args:
        review_id: ID of the review to update
        review_data: The updated review content and/or rating
        db_session: Database session for executing queries
        current_user: The authenticated user attempting the update

    Returns:
        schemas.Review: The updated review with like/dislike counts

    Raises:
        HTTPException: If the review is not found or user is not authorized
    """
    # Use the operation function that includes like/dislike counts
    return review_operations.update_review_with_counts(
        db_session,
        review_id,
        review_data,
        current_user
    )


@router.delete(
    "/reviews/{review_id}",
    response_model=schemas.Review,
    dependencies=[Depends(rate_limit)]
)
def delete_review(
    review_id: int,
    db_session: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Delete a review.

    Args:
        review_id: ID of the review to delete
        db_session: Database session for executing queries
        current_user: The authenticated user attempting the deletion

    Returns:
        schemas.Review: The deleted review with like/dislike counts

    Raises:
        HTTPException: If the review is not found or user is not authorized
    """
    # Use the operation function that includes like/dislike counts
    return review_operations.delete_review_with_counts(
        db_session,
        review_id,
        current_user
    )


@router.post(
    "/reviews/react",
    dependencies=[Depends(rate_limit)]
)
def react_to_review(
    reaction_data: schemas.ReactionIn,
    db_session: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Add or update a reaction (like/dislike) to a review.

    Args:
        reaction_data: The review ID and reaction value
        db_session: Database session for executing queries
        current_user: The authenticated user reacting to the review

    Returns:
        dict: Information about the action performed

    Raises:
        HTTPException: If the review is not found or reaction value is invalid
    """
    # React to the review
    result = review_operations.react_to_review(
        db_session,
        reaction_data.review_id,
        current_user.id,
        reaction_data.value
    )

    # Get updated counts
    counts = review_operations.get_review_likes_dislikes(
        db_session,
        reaction_data.review_id
    )

    return {
        "action": result.get("action"),
        "value": result.get("value"),
        "likes": counts["likes"],
        "dislikes": counts["dislikes"]
    }
