from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.security import get_current_user, rate_limit
from operations import book_operations
from typing import List
import os
import uuid
from sqlalchemy import func


router = APIRouter(prefix="/books", tags=["books"])


@router.post(
        "/",
        response_model=schemas.Book,
        dependencies=[Depends(rate_limit)]
        )
def create_book(
    book_data: schemas.BookCreate,
    db_session: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a new book for the current user.

    Args:
        book_data: The book data to create
        db_session: Database session
        current_user: The authenticated user

    Returns:
        schemas.Book: The created book
    """
    return book_operations.create_book(db_session, book_data, current_user.id)


@router.get(
        "/",
        response_model=List[schemas.Book],
        dependencies=[Depends(rate_limit)]
        )
def get_books(
    skip: int = 0,
    limit: int = 10,
    search_query: str = None,
    author_filter: str = None,
    min_rating_filter: float = None,
    db_session: Session = Depends(get_db)
):
    """
    Retrieve a list of books with optional filters.

    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        search_query: Filter books by title
        author_filter: Filter books by author
        min_rating_filter: Minimum average rating filter
        db_session: Database session

    Returns:
        List[schemas.Book]: List of books matching the criteria
    """
    return book_operations.get_books_with_filters(
        db_session,
        skip,
        limit,
        search_query,
        author_filter,
        min_rating_filter
    )


@router.get(
        "/{book_id}",
        response_model=schemas.Book,
        dependencies=[Depends(rate_limit)]
        )
def get_book(book_id: int, db_session: Session = Depends(get_db)):
    """
    Get a book by ID, including average rating.

    Args:
        book_id: ID of the book to retrieve
        db_session: Database session

    Returns:
        schemas.Book: The book with its average rating

    Raises:
        HTTPException: If the book is not found
    """
    db_book = book_operations.get_book_by_id(db_session, book_id)

    # Check if book exists
    if not db_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    # Calculate average rating if not already present
    if not hasattr(db_book, "avg_rating"):
        db_book.avg_rating = db_session.query(
            func.coalesce(func.avg(models.Review.rating), 0.0)
        ).filter(models.Review.book_id == book_id).scalar() or 0.0

    return db_book


@router.put(
        "/{book_id}",
        response_model=schemas.Book,
        dependencies=[Depends(rate_limit)]
        )
def update_book(
    book_id: int,
    book_data: schemas.BookUpdate,
    db_session: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update a book's details.

    Args:
        book_id: ID of the book to update
        book_data: The updated book data
        db_session: Database session
        current_user: The authenticated user

    Returns:
        schemas.Book: The updated book

    Raises:
        HTTPException: If the book is not found or user is not authorized
    """
    try:
        db_book = book_operations.update_book_info(
            db_session,
            book_id,
            book_data,
            current_user)
        return db_book

    except HTTPException as e:
        raise e   # re-raise exceptions
    except Exception:
        # Catch any unexpected errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unexpected error"
        )


@router.delete(
        "/{book_id}",
        response_model=schemas.Book,
        dependencies=[Depends(rate_limit)]
        )
def delete_book(
    book_id: int,
    db_session: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Delete a book.

    Args:
        book_id: ID of the book to delete
        db_session: Database session
        current_user: The authenticated user

    Returns:
        schemas.Book: The deleted book

    Raises:
        HTTPException: If the book is not found or user is not authorized
    """
    try:
        db_book = book_operations.delete_book_record(
            db_session,
            book_id,
            current_user)
        return db_book

    except HTTPException as e:
        raise e   # re-raise exceptions

    except Exception:
        # Catch any unexpected errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unexpected error"
        )


@router.post("/{book_id}/cover", dependencies=[Depends(rate_limit)])
def upload_cover_image(
    book_id: int,
    file: UploadFile = File(...),
    db_session: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Upload a cover image for a book.

    Args:
        book_id: ID of the book
        file: The image file to upload
        db_session: Database session
        current_user: The authenticated user

    Returns:
        dict: The URL of the uploaded cover image

    Raises:
        HTTPException: If the book is not found or user is not authorized
    """
    book = book_operations.get_book_by_id(db_session, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    # Check authorization
    if current_user.role != models.UserRole.admin\
            and book.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to change this book's cover"
        )

    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    upload_directory = os.path.abspath("./uploads")
    destination_path = os.path.join(upload_directory, unique_filename)

    # Create upload directory if it doesn't exist
    os.makedirs(upload_directory, exist_ok=True)

    # Save file
    with open(destination_path, "wb") as buffer:
        buffer.write(file.file.read())

    # Update book record
    book.cover_image = f"/uploads/{unique_filename}"
    db_session.commit()
    db_session.refresh(book)

    return {"cover_image": book.cover_image}
