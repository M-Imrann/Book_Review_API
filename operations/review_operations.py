from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app import models, schemas
from typing import List
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status


def add_reaction_counts_to_review(
    db_session: Session,
    review: models.Review
) -> models.Review:
    """
    function to add likes and dislikes counts to a review object.

    Args:
        db_session: Database session for executing queries
        review: The review object to add counts to

    Returns:
        models.Review: The review with likes and dislikes counts added
    """
    counts = get_review_likes_dislikes(db_session, review.id)
    setattr(review, "likes", counts["likes"])
    setattr(review, "dislikes", counts["dislikes"])
    return review


def create_review_with_counts(
    db_session: Session,
    review_data: schemas.ReviewCreate,
    user_id: int
) -> models.Review:
    """
    Create a new review for a book and include like/dislike counts.

    Args:
        db_session: Database session for executing queries
        review_data: Review data containing content, rating, and book ID
        user_id: ID of the user creating the review

    Returns:
        models.Review: The newly created review object with like/dislike counts

    Raises:
        HTTPException: If the specified book does not exist
    """
    # Check if the book exists before creating a review
    book = db_session.query(models.Book).filter(
        models.Book.id == review_data.book_id
    ).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    # Create a new review instance with the provided data
    db_review = models.Review(
        content=review_data.content,
        rating=review_data.rating,
        user_id=user_id,
        book_id=review_data.book_id
    )

    # Add the review to the session and commit to save to database
    db_session.add(db_review)
    db_session.commit()
    # Refresh the instance to get any database-generated values
    db_session.refresh(db_review)

    # Add like/dislike counts to the review
    return add_reaction_counts_to_review(db_session, db_review)


def get_reviews_for_book_with_counts(
    db_session: Session,
    book_id: int,
    skip: int = 0,
    limit: int = 20
) -> List[models.Review]:
    """
    Retrieve all reviews for a specific book with pagination and
    include like/dislike counts.

    Args:
        db_session: Database session for executing queries
        book_id: ID of the book to get reviews for
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return

    Returns:
        List[models.Review]: List of review objects with like/dislike counts
    """
    # Query reviews for the specified book
    reviews = db_session.query(models.Review).options(
        # Load only specific fields from the user to avoid unnecessary data
        joinedload(models.Review.user).load_only(
            models.User.id,
            models.User.email
        ),
        # Load all reactions for each review
        joinedload(models.Review.reactions)
    ).filter(
        models.Review.book_id == book_id
    ).offset(skip).limit(limit).all()

    # Add like/dislike counts to each review
    return [
        add_reaction_counts_to_review(db_session, review)
        for review in reviews
    ]


def update_review_with_counts(
    db_session: Session,
    review_id: int,
    review_data: schemas.ReviewUpdate,
    current_user: models.User
) -> models.Review:
    """
    Update the content of a review if the user is the owner or an admin
    and include like/dislike counts.

    Args:
        db_session: Database session for executing queries
        review_id: ID of the review to update
        review_data: New review data to update
        current_user: The user attempting to update the review

    Returns:
        models.Review: The updated review object with like/dislike counts

    Raises:
        HTTPException: If the review is not found or user is not authorized
    """
    # Find the review by ID
    db_review = db_session.query(models.Review).filter(
        models.Review.id == review_id
    ).first()

    # Check if the review exists
    if not db_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )

    # Check if the user is authorized (either the owner or an admin)
    if not (
        current_user.role == models.UserRole.admin
            or db_review.user_id == current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this review"
        )

    # Update only the fields that were provided in the request
    for key, value in review_data.dict(exclude_unset=True).items():
        setattr(db_review, key, value)

    # Commit changes to the database
    db_session.commit()
    # Refresh the instance to get updated values
    db_session.refresh(db_review)

    # Add like/dislike counts to the review
    return add_reaction_counts_to_review(db_session, db_review)


def delete_review_with_counts(
    db_session: Session,
    review_id: int,
    current_user: models.User
) -> models.Review:
    """
    Delete a review if the user is the owner or an admin and include
    like/dislike counts.

    Args:
        db_session: Database session for executing queries
        review_id: ID of the review to delete
        current_user: The user attempting to delete the review

    Returns:
        models.Review: The deleted review object with like/dislike counts

    Raises:
        HTTPException: If the review is not found or user is not authorized
    """
    # Find the review by ID
    db_review = db_session.query(models.Review).filter(
        models.Review.id == review_id
    ).first()

    # Check if the review exists
    if not db_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )

    # Check if the user is authorized (either the owner or an admin)
    if not (
        current_user.role == models.UserRole.admin
            or db_review.user_id == current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this review"
        )

    # Add like/dislike counts to the review before deletion
    add_reaction_counts_to_review(db_session, db_review)

    # Delete the review from the database
    db_session.delete(db_review)
    db_session.commit()

    return db_review


# Keep the original functions for backward compatibility
def create_review(
    db_session: Session,
    review_data: schemas.ReviewCreate,
    user_id: int
) -> models.Review:
    """Create a new review without counts (for internal use)"""
    return create_review_with_counts(db_session, review_data, user_id)


def get_reviews_for_book(
    db_session: Session,
    book_id: int,
    skip: int = 0,
    limit: int = 20
) -> List[models.Review]:
    """Get reviews without counts (for internal use)"""
    return get_reviews_for_book_with_counts(db_session, book_id, skip, limit)


def update_review_content(
    db_session: Session,
    review_id: int,
    review_data: schemas.ReviewUpdate,
    current_user: models.User
) -> models.Review:
    """Update a review without counts (for internal use)"""
    return update_review_with_counts(
        db_session, review_id, review_data, current_user
    )


def delete_review_record(
    db_session: Session,
    review_id: int,
    current_user: models.User
) -> models.Review:
    """Delete a review without counts (for internal use)"""
    return delete_review_with_counts(db_session, review_id, current_user)


# The following functions remain unchanged
def get_review_by_id(db_session: Session, review_id: int) -> models.Review:
    """
    Retrieve a single review by its ID.

    Args:
        db_session: Database session for executing queries
        review_id: ID of the review to retrieve

    Returns:
        models.Review: The review object if found, None otherwise
    """
    return db_session.query(models.Review).filter(
        models.Review.id == review_id
    ).first()


def react_to_review(
    db_session: Session,
    review_id: int,
    user_id: int,
    reaction_value: int
) -> dict:
    """
    Add, update, or remove a reaction (like/dislike) to a review.

    Args:
        db_session: Database session for executing queries
        review_id: ID of the review to react to
        user_id: ID of the user reacting to the review
        reaction_value: 1 for like, -1 for dislike

    Returns:
        dict: Information about the action performed and the reaction value

    Raises:
        HTTPException: If the review is not found or reaction value is invalid
        ValueError: If the reaction value is not 1 or -1
    """
    # Validate the reaction value
    if reaction_value not in (1, -1):
        raise ValueError("Reaction value must be 1 (like) or -1 (dislike)")

    # Check if the review exists
    review = db_session.query(models.Review).filter(
        models.Review.id == review_id
    ).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )

    # Check if the user has already reacted to this review
    existing_reaction = db_session.query(models.ReviewReaction).filter(
        models.ReviewReaction.review_id == review_id,
        models.ReviewReaction.user_id == user_id
    ).first()

    if existing_reaction:
        # If the user is reacting with the same value, remove the reaction
        if existing_reaction.value == reaction_value:
            db_session.delete(existing_reaction)
            db_session.commit()
            return {"action": "removed"}
        else:
            # If the user is changing their reaction, update it
            existing_reaction.value = reaction_value
            db_session.commit()
            db_session.refresh(existing_reaction)
            return {"action": "updated", "value": existing_reaction.value}
    else:
        # If the user hasn't reacted before, create a new reaction
        new_reaction = models.ReviewReaction(
            review_id=review_id,
            user_id=user_id,
            value=reaction_value
        )
        db_session.add(new_reaction)

        try:
            db_session.commit()
            return {"action": "created", "value": reaction_value}
        except IntegrityError:
            # Handle race conditions where reaction created by another process
            db_session.rollback()
            existing_reaction = db_session.query(models.ReviewReaction).filter(
                models.ReviewReaction.review_id == review_id,
                models.ReviewReaction.user_id == user_id
            ).first()
            if existing_reaction:
                existing_reaction.value = reaction_value
                db_session.commit()
                return {"action": "updated", "value": reaction_value}


def get_review_likes_dislikes(db_session: Session, review_id: int) -> dict:
    """
    Count the number of likes and dislikes for a review.

    Args:
        db_session: Database session for executing queries
        review_id: ID of the review to count reactions for

    Returns:
        dict: Dictionary with counts of likes and dislikes
    """
    # Count the number of likes (reactions with value = 1)
    likes_count = db_session.query(func.count()).filter(
        models.ReviewReaction.review_id == review_id,
        models.ReviewReaction.value == 1
    ).scalar()

    # Count the number of dislikes (reactions with value = -1)
    dislikes_count = db_session.query(func.count()).filter(
        models.ReviewReaction.review_id == review_id,
        models.ReviewReaction.value == -1
    ).scalar()

    # Return the counts, defaulting to 0 if None
    return {"likes": likes_count or 0, "dislikes": dislikes_count or 0}
