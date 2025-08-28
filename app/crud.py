from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from . import models, schemas
from typing import List, Optional
from sqlalchemy.exc import IntegrityError


def create_book(db: Session, book: schemas.BookCreate, user_id: int):
    """
    Create a new book.

    Args:
        db: SQLAlchemy database session.
        book: Book data to create.
        user_id: ID of the owner.

    Returns:
        Created book object.
    """

    db_book = models.Book(**book.dict(exclude_unset=True), owner_id=user_id)
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book


def get_books(
        db: Session,
        skip: int = 0,
        limit: int = 10,
        q: Optional[str] = None,
        author: Optional[str] = None,
        min_rating: Optional[float] = None
        ):
    """
    get_books function will retrieve books with optional 
    filters and average ratings.

    Args:
        db: SQLAlchemy database session.
        skip: Number of records to skip.
        limit: Number of records to return.
        q: Filter books by title.
        author: Filter books by author.
        min_rating: Minimum average rating filter.

    Returns:
        List of books with average ratings.
    """
    avg_rating_col = func.coalesce(
        func.avg(models.Review.rating), 0.0).label("avg_rating")

    query = (
        db.query(models.Book, avg_rating_col)
        .outerjoin(models.Review)
        .group_by(models.Book.id)
    )
    if q:
        query = query.filter(models.Book.title.ilike(f"%{q}%"))
    if author:
        query = query.filter(models.Book.author.ilike(f"%{author}%"))
    if min_rating is not None:
        query = query.having(avg_rating_col >= float(min_rating))

    results = query.order_by(
        desc(avg_rating_col),
        models.Book.title
        ).offset(skip).limit(limit).all()
    return [{
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "description": book.description,
        "owner_id": book.owner_id,
        "avg_rating": float(avg),
        "cover_image": book.cover_image,
    } for book, avg in results]


def get_book(db: Session, book_id: int):
    """
    get_book function will get a single book by ID.

    Args:
        db: SQLAlchemy database session.
        book_id: Book ID to fetch.

    Returns:
        Book object or None if not found.
    """
    return db.query(models.Book).options(
        joinedload(models.Book.owner).load_only(
            models.User.id,
            models.User.email,
            models.User.role
            ),
        joinedload(models.Book.reviews)
    ).filter(models.Book.id == book_id).first()


def update_book(
        db: Session,
        book_id: int,
        book: schemas.BookUpdate,
        user_id: int,
        is_admin: bool = False
        ):
    """
    update_book function will update a book's information.

    Args:
        db: SQLAlchemy database session.
        book_id: Book ID to update.
        book: Data to update.
        user_id: ID of the current user.
        is_admin: Whether current user is admin.

    Returns:
        Updated book or None if not found/unauthorized.
    """
    q = db.query(models.Book).filter(models.Book.id == book_id)
    if not is_admin:
        q = q.filter(models.Book.owner_id == user_id)
    db_book = q.first()
    if not db_book:
        return None
    for key, value in book.dict(exclude_unset=True).items():
        setattr(db_book, key, value)
    db.commit()
    db.refresh(db_book)
    return db_book


def delete_book(
        db: Session,
        book_id: int,
        user_id: int,
        is_admin: bool = False
        ):
    """
    delete_book function will delete a book.

    Args:
        db: SQLAlchemy database session.
        book_id: ID of the book to delete.
        user_id: ID of the current user.
        is_admin: Whether the user is admin.

    Returns:
        Deleted book object or None if not found/unauthorized.
    """

    q = db.query(models.Book).filter(models.Book.id == book_id)
    if not is_admin:
        q = q.filter(models.Book.owner_id == user_id)
    db_book = q.first()
    if not db_book:
        return None
    db.delete(db_book)
    db.commit()
    return db_book


def create_review(db: Session, review_in: schemas.ReviewCreate, user_id: int):
    """
    create review function will create a new review for a book.

    Args:
        db: SQLAlchemy database session.
        review_in: Review data.
        user_id: ID of the user creating the review.

    Returns:
        Created review or None if book not found.
    """
    book = db.query(models.Book)\
        .filter(models.Book.id == review_in.book_id).first()
    if not book:
        return None
    db_review = models.Review(
        content=review_in.content,
        rating=review_in.rating,
        user_id=user_id,
        book_id=review_in.book_id
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review


def get_reviews_for_book(
        db: Session,
        book_id: int,
        skip: int = 0,
        limit: int = 20) -> List[models.Review]:
    """
    get_reviews function will get reviews for a specific book.

    Args:
        db: SQLAlchemy database session.
        book_id: ID of the book.
        skip: Number of records to skip.
        limit: Max number of records to return.

    Returns:
        List of reviews for the book.
    """
    return db.query(models.Review).options(
        joinedload(models.Review.user).load_only(
            models.User.id,
            models.User.email
            ),
        joinedload(models.Review.reactions)
    ).filter(models.Review.book_id == book_id).offset(skip).limit(limit).all()


def get_review(db: Session, review_id: int):
    """
    get_review function will get a single review by ID.

    Args:
        db: SQLAlchemy database session.
        review_id: Review ID.

    Returns:
        Review object or None if not found.
    """
    return db.query(models.Review)\
        .filter(models.Review.id == review_id).first()


def update_review(
        db: Session,
        review_id: int,
        review_in: schemas.ReviewUpdate,
        user_id: int,
        is_admin: bool = False
        ):
    """
    update_review function will update a review.

    Args:
        db: SQLAlchemy database session.
        review_id: Review ID.
        review_in: Update data.
        user_id: Current user ID.
        is_admin: Whether the user is admin.

    Returns:
        Updated review or None if not found/unauthorized.
    """
    q = db.query(models.Review).filter(models.Review.id == review_id)
    if not is_admin:
        q = q.filter(models.Review.user_id == user_id)
    db_review = q.first()
    if not db_review:
        return None
    for key, val in review_in.dict(exclude_unset=True).items():
        setattr(db_review, key, val)
    db.commit()
    db.refresh(db_review)
    return db_review


def delete_review(
        db: Session,
        review_id: int,
        user_id: int,
        is_admin: bool = False
        ):
    """
    delete_review function will delete a review.

    Args:
        db: SQLAlchemy database session.
        review_id: Review ID.
        user_id: Current user ID.
        is_admin: Whether the user is admin.

    Returns:
        Deleted review or None if not found/unauthorized.
    """
    q = db.query(models.Review).filter(models.Review.id == review_id)
    if not is_admin:
        q = q.filter(models.Review.user_id == user_id)
    db_review = q.first()
    if not db_review:
        return None
    db.delete(db_review)
    db.commit()
    return db_review


def react_review(db: Session, review_id: int, user_id: int, value: int):
    """
    react_review function will react to a review.

    Args:
        db: SQLAlchemy database session.
        review_id: Review ID.
        user_id: User ID reacting.
        value: 1 for like, -1 for dislike.

    Returns:
        React Created.
    """
    if value not in (1, -1):
        raise ValueError("Reaction value must be 1 (like) or -1 (dislike)")
    review = db.query(models.Review)\
        .filter(models.Review.id == review_id).first()
    if not review:
        return None

    existing = db.query(models.ReviewReaction).filter(
        models.ReviewReaction.review_id == review_id,
        models.ReviewReaction.user_id == user_id
    ).first()

    if existing:
        if existing.value == value:
            db.delete(existing)
            db.commit()
            return {"action": "removed"}
        else:
            existing.value = value
            db.commit()
            db.refresh(existing)
            return {"action": "updated", "value": existing.value}
    else:
        new_reaction = models.ReviewReaction(
            review_id=review_id,
            user_id=user_id,
            value=value
            )
        db.add(new_reaction)
        try:
            db.commit()
            return {"action": "created", "value": value}
        except IntegrityError:
            db.rollback()
            # If a race occurred, fetch and update
            existing = db.query(models.ReviewReaction).filter(
                models.ReviewReaction.review_id == review_id,
                models.ReviewReaction.user_id == user_id
            ).first()
            if existing:
                existing.value = value
                db.commit()
                return {"action": "updated", "value": value}
            raise


def review_likes_dislikes(db: Session, review_id: int):
    likes = db.query(func.count()).filter(
        models.ReviewReaction.review_id == review_id,
        models.ReviewReaction.value == 1
    ).scalar()
    dislikes = db.query(func.count()).filter(
        models.ReviewReaction.review_id == review_id,
        models.ReviewReaction.value == -1
    ).scalar()
    return {"likes": likes or 0, "dislikes": dislikes or 0}
