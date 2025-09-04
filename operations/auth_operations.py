from sqlalchemy.orm import Session
from app import models, schemas
from app.security import get_password_hash
from fastapi import HTTPException, status


def create_user(
        db_session: Session,
        user_data: schemas.UserCreate) -> models.User:
    """
    Create a new user in the database.

    Args:
        db_session: Database session
        user_data: User creation data

    Returns:
        models.User: The created user

    Raises:
        HTTPException: If the email is already registered
    """
    existing_user = db_session.query(models.User).filter(
        models.User.email == user_data.email
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    try:
        hashed_password = get_password_hash(user_data.password)
        user = models.User(
            email=user_data.email,
            hashed_password=hashed_password,
            role=user_data.role
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user due to server error."
        )


def promote_user_to_admin(db_session: Session, user_id: int) -> models.User:
    """
    Promote a user to admin role.

    Args:
        db_session: Database session
        user_id: ID of the user to promote

    Returns:
        models.User: The promoted user

    Raises:
        HTTPException: If the user is not found
    """
    user = db_session.query(models.User).filter(
        models.User.id == user_id
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    try:
        user.role = models.UserRole.ADMIN
        db_session.commit()
        db_session.refresh(user)
        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to promote user due to server error."
        )
