from fastapi import (
    FastAPI, Depends, HTTPException,
    status, APIRouter, UploadFile, File
)
from sqlalchemy.orm import Session
from sqlalchemy import func
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional
from fastapi.staticfiles import StaticFiles
import os
import uuid

from app import crud, models, schemas, security
from .database import engine, Base, get_db


app = FastAPI()
router = APIRouter(prefix="/books", tags=["books"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

Base.metadata.create_all(bind=engine)

# --- Static mount for uploaded covers ---
UPLOAD_DIR = os.path.abspath("./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.post("/register", response_model=schemas.UserRead)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    Raises an HTTPException if the email is already registered.
    Returns the created user.
    """
    existing = db.query(models.User)\
        .filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = pwd_context.hash(user_in.password)
    user = models.User(
        email=user_in.email,
        hashed_password=hashed_pw, role="user"
        )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/login")
def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
        ):
    """
    login function will authenticate a user and return a JWT access token.

    Raises an HTTPException if credentials are invalid.
    """
    user = db.query(models.User)\
        .filter(models.User.email == form_data.username).first()
    if not user or not security.verify_password(
            form_data.password,
            user.hashed_password
            ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
            )
    access_token = security.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post(
        "/admin/promote/{user_id}",
        dependencies=[Depends(security.require_admin)]
        )
def promote_user(user_id: int, db: Session = Depends(get_db)):
    """
    promote_user function will promote a user to admin role.

    Only admins can promote users to admin.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.role = "admin"
    db.commit()
    return {"status": "ok", "user_id": user_id, "role": "admin"}


@router.post(
        "/",
        response_model=schemas.Book,
        dependencies=[Depends(security.rate_limit)]
        )
def create_book(
        book: schemas.BookCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(security.get_current_user)
        ):
    """
    Create a new book for the current user.
    """
    return crud.create_book(db=db, book=book, user_id=current_user.id)


@router.get(
        "/",
        response_model=List[schemas.Book],
        dependencies=[Depends(security.rate_limit)]
        )
def get_books(
        skip: int = 0,
        limit: int = 10,
        q: Optional[str] = None,
        author: Optional[str] = None,
        min_rating: Optional[float] = None,
        db: Session = Depends(get_db)
        ):
    """
    Retrieve a list of books.
    """
    return crud.get_books(
        db=db,
        skip=skip,
        limit=limit,
        q=q,
        author=author,
        min_rating=min_rating
        )


@router.get(
        "/{book_id}",
        response_model=schemas.Book,
        dependencies=[Depends(security.rate_limit)]
        )
def get_book(book_id: int, db: Session = Depends(get_db)):
    """
    get book function will get book by ID, including average rating.

    Raises 404 if the book is not found.
    """
    db_book = crud.get_book(db=db, book_id=book_id)
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    if not hasattr(db_book, "avg_rating"):
        db_book.avg_rating = db.query(
            func.coalesce(func.avg(models.Review.rating), 0.0))\
                .filter(models.Review.book_id == book_id).scalar() or 0.0
    return db_book


@router.put(
        "/{book_id}",
        response_model=schemas.Book,
        dependencies=[Depends(security.rate_limit)]
        )
def update_book(
        book_id: int,
        book: schemas.BookUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(security.get_current_user)
        ):
    """
    update_book function will update a book's details.

    Raises 404 if book not found or unauthorized.
    """
    db_book = crud.update_book(
        db=db,
        book_id=book_id,
        book=book,
        user_id=current_user.id,
        is_admin=(current_user.role == "admin")
        )
    if not db_book:
        raise HTTPException(
            status_code=404,
            detail="Book not found or not authorized"
            )
    return db_book


@router.delete(
        "/{book_id}",
        response_model=schemas.Book,
        dependencies=[Depends(security.rate_limit)]
        )
def delete_book(
        book_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(security.get_current_user)
        ):
    """
    delete_book function will delete a book.

    Raises 404 if book not found or unauthorized.
    """
    db_book = crud.delete_book(
        db=db,
        book_id=book_id,
        user_id=current_user.id,
        is_admin=(current_user.role == "admin")
        )
    if not db_book:
        raise HTTPException(
            status_code=404,
            detail="Book not found or not authorized"
            )
    return db_book


@router.post("/{book_id}/cover")
def upload_cover(
        book_id: int,
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(security.get_current_user)
        ):
    """
    upload_cover function will upload a cover image for a book.

    Only the owner or admin can upload/change the cover.

    Return:
        Returns the URL of the uploaded cover.
    """
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "Book not found")
    if current_user.role != "admin" and book.owner_id != current_user.id:
        raise HTTPException(403, "Not authorized to change cover")
    ext = os.path.splitext(file.filename)[1].lower()
    fname = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(UPLOAD_DIR, fname)
    with open(dest, "wb") as f:
        f.write(file.file.read())
    book.cover_image = f"/uploads/{fname}"
    db.commit()
    db.refresh(book)
    return {"cover_image": book.cover_image}


@router.post(
        "/reviews/",
        response_model=schemas.Review,
        dependencies=[Depends(security.rate_limit)]
        )
def create_review(
        review_in: schemas.ReviewCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(security.get_current_user)
        ):
    """
    create_review function will create a review for a book by the current user.

    Returns:
        Returns review with likes/dislikes counts.

    Raises 404 if book not found.
    """
    db_review = crud.create_review(
        db=db,
        review_in=review_in,
        user_id=current_user.id
        )
    if not db_review:
        raise HTTPException(status_code=404, detail="Book not found")
    counts = crud.review_likes_dislikes(db, db_review.id)
    setattr(db_review, "likes", counts["likes"])
    setattr(db_review, "dislikes", counts["dislikes"])
    return db_review


@router.get(
        "/{book_id}/reviews",
        response_model=List[schemas.Review],
        dependencies=[Depends(security.rate_limit)]
        )
def get_reviews(
        book_id: int,
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db)
        ):
    """
    get_reviews function will get all reviews for a
    specific book, including likes/dislikes counts.
    """
    reviews = crud.get_reviews_for_book(
        db=db,
        book_id=book_id,
        skip=skip,
        limit=limit
        )
    out = []
    for r in reviews:
        counts = crud.review_likes_dislikes(db, r.id)
        setattr(r, "likes", counts["likes"])
        setattr(r, "dislikes", counts["dislikes"])
        out.append(r)
    return out


@router.put(
        "/reviews/{review_id}",
        response_model=schemas.Review,
        dependencies=[Depends(security.rate_limit)]
        )
def update_review(
        review_id: int,
        review_in: schemas.ReviewUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(security.get_current_user)
        ):
    """
    update_review function will update a review.

    Returns:
        Returns updated review with likes/dislikes.

    Raises 404 if review not found or unauthorized.
    """
    db_review = crud.update_review(
        db=db,
        review_id=review_id,
        review_in=review_in,
        user_id=current_user.id,
        is_admin=(current_user.role == "admin")
        )
    if not db_review:
        raise HTTPException(
            status_code=404,
            detail="Review not found or not authorized"
            )
    counts = crud.review_likes_dislikes(db, db_review.id)
    setattr(db_review, "likes", counts["likes"])
    setattr(db_review, "dislikes", counts["dislikes"])
    return db_review


@router.delete(
        "/reviews/{review_id}",
        response_model=schemas.Review,
        dependencies=[Depends(security.rate_limit)]
        )
def delete_review(
        review_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(security.get_current_user)
        ):
    """
    delete_review function will delete a review.

    Returns:
        Returns deleted review with likes/dislikes.

    Raises 404 if review not found or unauthorized.
    """
    db_review = crud.delete_review(
        db=db,
        review_id=review_id,
        user_id=current_user.id,
        is_admin=(current_user.role == "admin")
        )
    if not db_review:
        raise HTTPException(
            status_code=404,
            detail="Review not found or not authorized"
            )
    counts = crud.review_likes_dislikes(db, db_review.id)
    setattr(db_review, "likes", counts["likes"])
    setattr(db_review, "dislikes", counts["dislikes"])
    return db_review


@router.post("/reviews/react", dependencies=[Depends(security.rate_limit)])
def react_to_review(
        reaction_in: schemas.ReactionIn,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(security.get_current_user)
        ):
    """
    raect_to_review function will Add or update a reaction
    (like/dislike) to a review by the current user.

    Returns:
        Returns the updated likes and dislikes counts for the review.

    Raises 404 if review not found.
    """
    res = crud.react_review(
        db=db,
        review_id=reaction_in.review_id,
        user_id=current_user.id,
        value=reaction_in.value
        )
    if res is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return res


app.include_router(router)
