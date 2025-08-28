from pydantic import BaseModel, EmailStr, conint
from typing import Optional


class UserCreate(BaseModel):
    """
    Schema for User Create
    """
    email: EmailStr
    password: str


class UserRead(BaseModel):
    """
    Schema for User Read
    """
    id: int
    email: EmailStr
    role: str

    class Config:
        from_attributes = True


class BookBase(BaseModel):
    """
    Schema for Book
    """
    title: str
    author: str
    description: Optional[str] = None


class BookCreate(BookBase):
    """
    Schema for Book Create
    """
    cover_image: Optional[str] = None


class BookUpdate(BaseModel):
    """
    Schema for Book Update
    """
    title: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None


class Book(BookBase):
    """
    Schema for reading the data
    """
    id: int
    owner_id: int
    avg_rating: Optional[float] = 0.0
    cover_image: Optional[str] = None

    class Config:
        from_attributes = True


class ReviewBase(BaseModel):
    """
    Schema for Review
    """
    content: Optional[str] = None
    rating: conint(ge=1, le=5)


class ReviewCreate(ReviewBase):
    """
    Schema for Review Create
    """
    book_id: int


class ReviewUpdate(BaseModel):
    """
    Schema for Review Update
    """
    content: Optional[str] = None
    rating: Optional[conint(ge=1, le=5)] = None


class Review(ReviewBase):
    """
    Schema for Review reading
    """
    id: int
    user_id: int
    book_id: int
    likes: int = 0
    dislikes: int = 0

    class Config:
        from_attributes = True


class ReactionIn(BaseModel):
    """
    Schema for Review Reacting
    """
    review_id: int
    value: int

    class Config:
        json_schema_extra = {"example": {"review_id": 1, "value": 1}}
