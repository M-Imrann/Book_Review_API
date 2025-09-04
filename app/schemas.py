from pydantic import BaseModel, EmailStr, conint
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    """
    Enumeration representing user roles in the system.

    """
    user = "user"
    admin = "admin"


class UserCreate(BaseModel):
    """
    Schema for creating a new user.
    """
    email: EmailStr
    password: str
    role: UserRole

    class Config:
        """
        Pydantic configuration for the UserCreate schema.
        """
        # Example of how this schema would be used
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "password123",
                "role": "user"
            }
        }


class UserRead(BaseModel):
    """
    Schema for reading user data excluding password.
    """
    id: int
    email: EmailStr
    role: UserRole

    class Config:
        """
        Pydantic configuration for the UserRead schema.
        """
        from_attributes = True


class BookBase(BaseModel):
    """
    Base schema for book data containing common fields.
    """
    title: str
    author: str
    description: Optional[str] = None

    class Config:
        """
        Pydantic configuration for the BookBase schema.
        """
        # Example of how this schema would be used
        json_schema_extra = {
            "example": {
                "title": "The Great Gatsby",
                "author": "F. Scott Fitzgerald",
                "description": "A classic American novel set in the Jazz Age"
            }
        }


class BookCreate(BookBase):
    """
    Schema for creating a new book.
    """
    cover_image: Optional[str] = None


class BookUpdate(BaseModel):
    """
    Schema for updating an existing book.

    All fields are optional as we may only want to update specific attributes.
    """
    title: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None


class Book(BookBase):
    """
    Complete schema for book data to read.
    """
    id: int
    owner_id: int
    avg_rating: Optional[float] = 0.0
    cover_image: Optional[str] = None

    class Config:
        """
        Pydantic configuration for the Book schema.
        """
        from_attributes = True


class ReviewBase(BaseModel):
    """
    Base schema for review.
    """
    content: Optional[str] = None
    rating: conint(ge=1, le=5)


class ReviewCreate(ReviewBase):
    """
    Schema for creating a new review.
    """
    book_id: int


class ReviewUpdate(BaseModel):
    """
    Schema for updating an existing review.
    """
    content: Optional[str] = None
    rating: Optional[conint(ge=1, le=5)] = None


class Review(ReviewBase):
    """
    Complete schema for review to read.
    """
    id: int
    user_id: int
    book_id: int
    likes: int = 0
    dislikes: int = 0

    class Config:
        """
        Pydantic configuration for the Review schema.
        """
        from_attributes = True


class ReactionIn(BaseModel):
    """
    Schema for submitting a reaction (like/dislike) to a review.
    """
    review_id: int
    value: int

    class Config:
        """
        Pydantic configuration for the ReactionIn schema.
        """
        # Example of how this schema would be used
        json_schema_extra = {
            "example": {
                "review_id": 1,
                "value": 1
            }
        }
