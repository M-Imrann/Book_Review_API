from sqlalchemy import (
    Column, Integer, String,
    ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func, select
from .database import Base


class User(Base):
    """
    Model/Table for User
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")

    books = relationship(
        "Book",
        back_populates="owner",
        cascade="all, delete-orphan"
        )
    reviews = relationship(
        "Review",
        back_populates="user",
        cascade="all, delete-orphan"
        )
    reactions = relationship(
        "ReviewReaction",
        back_populates="user",
        cascade="all, delete-orphan"
        )


class Book(Base):
    """
    Model/Table for Book
    """
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    cover_image = Column(String, nullable=True)

    owner = relationship("User", back_populates="books")
    reviews = relationship(
        "Review",
        back_populates="book",
        cascade="all, delete-orphan"
        )

    @hybrid_property
    def avg_rating(self):
        if not self.reviews:
            return 0.0
        total = sum(r.rating for r in self.reviews)
        return total / len(self.reviews)

    @avg_rating.expression
    def avg_rating(cls):
        return (
            select(func.coalesce(func.avg(Review.rating), 0.0))
            .where(Review.book_id == cls.id)
            .scalar_subquery()
        )


class Review(Base):
    """
    Model/Table for Review
    """
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=True)
    rating = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)

    user = relationship("User", back_populates="reviews")
    book = relationship("Book", back_populates="reviews")
    reactions = relationship(
        "ReviewReaction",
        back_populates="review",
        cascade="all, delete-orphan"
        )


class ReviewReaction(Base):
    """
    Model/Table for Review Reaction
    """
    __tablename__ = "review_reactions"
    __table_args__ = (
        UniqueConstraint("user_id", "review_id", name="uix_user_review"),
        )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False)
    value = Column(Integer, nullable=False)

    user = relationship("User", back_populates="reactions")
    review = relationship("Review", back_populates="reactions")
