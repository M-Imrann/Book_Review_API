from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from app import models, schemas
from typing import List, Optional
from fastapi import HTTPException, status


def create_book(
        db_session: Session,
        book_data: schemas.BookCreate,
        user_id: int) -> models.Book:
    """
    Create a new book in the database.

    Args:
        db_session: Database session
        book_data: Book creation data
        user_id: ID of the user creating the book

    Returns:
        models.Book: The created book object
    """
    db_book = models.Book(
        **book_data.dict(exclude_unset=True),
        owner_id=user_id)
    db_session.add(db_book)
    db_session.commit()
    db_session.refresh(db_book)
    return db_book


def get_books_with_filters(
    db_session: Session,
    skip: int = 0,
    limit: int = 10,
    search_query: Optional[str] = None,
    author_filter: Optional[str] = None,
    min_rating_filter: Optional[float] = None
) -> List[models.Book]:
    """
    Retrieve books with optional filters and average ratings.

    Args:
        db_session: Database session
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        search_query: Filter books by title
        author_filter: Filter books by author
        min_rating_filter: Minimum average rating filter

    Returns:
        List[models.Book]: List of books with their average ratings
    """
    avg_rating_column = func.coalesce(
        func.avg(models.Review.rating), 0.0).label("avg_rating")

    query = (
        db_session.query(models.Book, avg_rating_column)
        .outerjoin(models.Review)
        .group_by(models.Book.id)
    )

    if search_query:
        query = query.filter(models.Book.title.ilike(f"%{search_query}%"))
    if author_filter:
        query = query.filter(models.Book.author.ilike(f"%{author_filter}%"))
    if min_rating_filter is not None:
        query = query.having(avg_rating_column >= float(min_rating_filter))

    results = query.order_by(
        desc(avg_rating_column),
        models.Book.title
    ).offset(skip).limit(limit).all()

    books_with_ratings = []
    for book, avg_rating in results:
        books_with_ratings.append({
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "description": book.description,
            "owner_id": book.owner_id,
            "avg_rating": float(avg_rating),
            "cover_image": book.cover_image,
        })

    return books_with_ratings


def get_book_by_id(db_session: Session, book_id: int) -> models.Book:
    """
    Get a single book by ID.

    Args:
        db_session: Database session
        book_id: ID of the book to retrieve

    Returns:
        models.Book: The book object or None if not found
    """
    return db_session.query(models.Book).options(
        joinedload(models.Book.owner).load_only(
            models.User.id,
            models.User.email,
            models.User.role
        ),
        joinedload(models.Book.reviews)
    ).filter(models.Book.id == book_id).first()


def update_book_info(
    db_session: Session,
    book_id: int,
    book_data: schemas.BookUpdate,
    current_user: models.User
) -> models.Book:
    """
    Update a book's information if user is owner or admin.

    Args:
        db_session: Database session
        book_id: ID of the book to update
        book_data: Updated book data
        current_user: The user attempting the update

    Returns:
        models.Book: The updated book object

    Raises:
        HTTPException: If the book is not found or user is not authorized
    """
    db_book = db_session.query(models.Book)\
        .filter(models.Book.id == book_id).first()

    if not db_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    # Check ownership or admin privileges
    if not (
        current_user.role == models.UserRole.admin
            or db_book.owner_id == current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this book"
        )

    for key, value in book_data.dict(exclude_unset=True).items():
        setattr(db_book, key, value)

    db_session.commit()
    db_session.refresh(db_book)
    return db_book


def delete_book_record(
    db_session: Session,
    book_id: int,
    current_user: models.User
) -> models.Book:
    """
    Delete a book if user is owner or admin.

    Args:
        db_session: Database session
        book_id: ID of the book to delete
        current_user: The user attempting the deletion

    Returns:
        models.Book: The deleted book object

    Raises:
        HTTPException: If the book is not found or user is not authorized
    """
    db_book = db_session.query(models.Book)\
        .filter(models.Book.id == book_id).first()

    if not db_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    # Check ownership or admin privileges
    if not (
        current_user.role == models.UserRole.admin
            or db_book.owner_id == current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this book"
        )

    db_session.delete(db_book)
    db_session.commit()
    return db_book
