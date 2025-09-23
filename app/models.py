from sqlalchemy import (
    Column, Integer, String, ForeignKey,
    Text, UniqueConstraint, Enum as SqlEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func, select
from .database import Base
from .schemas import UserRole


class User(Base):
    """
    SQLAlchemy model representing a user in the system.
    """
    __tablename__ = "users"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    # User's email address, must be unique and indexed
    email = Column(String, unique=True, index=True, nullable=False)
    # Hashed password for authentication security
    hashed_password = Column(String, nullable=False)
    # User's role, defaults to USER if not specified
    role = Column(SqlEnum(UserRole), nullable=False)

    # Relationship to books owned by this user
    # cascade="all, delete-orphan" ensures books are deleted if user is deleted
    books = relationship(
        "Book",
        back_populates="owner",
        cascade="all, delete-orphan"
    )

    # Relationship to reviews written by this user
    reviews = relationship(
        "Review",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # Relationship to reactions made by this user
    reactions = relationship(
        "ReviewReaction",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Book(Base):
    """
    SQLAlchemy model representing a book in the system.
    """
    __tablename__ = "books"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    # Title of the book, indexed for search functionality
    title = Column(String, index=True)
    # Author of the book, indexed for search functionality
    author = Column(String, index=True)
    # Optional description of the book
    description = Column(Text, nullable=True)
    # Foreign key to the user who owns/added the book
    owner_id = Column(Integer, ForeignKey("users.id"))
    # Optional URL or path to the book's cover image
    cover_image = Column(String, nullable=True)

    # Relationship to the user who owns this book
    owner = relationship("User", back_populates="books")

    # Relationship to reviews for this book
    reviews = relationship(
        "Review",
        back_populates="book",
        cascade="all, delete-orphan"
    )

    @hybrid_property
    def avg_rating(self):
        """
        Calculate the average rating for this book based on all its reviews.

        Returns:
            float: The average rating, or 0.0 if there are no reviews
        """
        if not self.reviews:
            return 0.0
        # Calculate the sum of all ratings
        total = sum(r.rating for r in self.reviews)
        # Return the average
        return total / len(self.reviews)

    @avg_rating.expression
    def avg_rating(cls):
        """
        SQL expression for calculating the average rating.

        Returns:
            SQL expression: A subquery that calculates the average rating
        """
        return (
            select(func.coalesce(func.avg(Review.rating), 0.0))
            .where(Review.book_id == cls.id)
            .scalar_subquery()
        )


class Review(Base):
    """
    SQLAlchemy model representing a review of a book.
    """
    __tablename__ = "reviews"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    # Optional text content of the review
    content = Column(Text, nullable=True)
    # Rating value (integer between 1 and 5)
    rating = Column(Integer, nullable=False)
    # Foreign key to the user who wrote the review
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Foreign key to the book being reviewed
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)

    # Relationship to the user who wrote this review
    user = relationship("User", back_populates="reviews")

    # Relationship to the book being reviewed
    book = relationship("Book", back_populates="reviews")

    # Relationship to reactions on this review
    reactions = relationship(
        "ReviewReaction",
        back_populates="review",
        cascade="all, delete-orphan"
    )


class ReviewReaction(Base):
    """
    SQLAlchemy model representing a user's reaction to a review.
    """
    __tablename__ = "review_reactions"

    # Unique constraint to prevent duplicate reactions from the same user
    __table_args__ = (
        UniqueConstraint("user_id", "review_id", name="uix_user_review"),
    )

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    # Foreign key to the user who reacted
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Foreign key to the review being reacted to
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False)
    # Reaction value (1 for like, -1 for dislike)
    value = Column(Integer, nullable=False)

    # Relationship to the user who made this reaction
    user = relationship("User", back_populates="reactions")
    # Relationship to the review this reaction is for
    review = relationship("Review", back_populates="reactions")
