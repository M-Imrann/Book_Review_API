from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.security import verify_password, create_access_token, require_admin
from operations import auth_operations


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=schemas.UserRead)
def register_user(
    user_data: schemas.UserCreate,
    db_session: Session = Depends(get_db)
):
    """
    Register a new user.

    Args:
        user_data: User registration data
        db_session: Database session

    Returns:
        schemas.UserRead: The created user

    Raises:
        HTTPException: If the email is already registered
    """
    user = auth_operations.create_user(db_session, user_data)
    return user


@router.post("/login")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db_session: Session = Depends(get_db)
):
    """
    Authenticate a user and return a JWT access token.

    Args:
        form_data: The login form data
        db_session: Database session

    Returns:
        dict: The access token and token type

    Raises:
        HTTPException: If the credentials are invalid
    """
    user = db_session.query(models.User).filter(
        models.User.email == form_data.username
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/promote/{user_id}", dependencies=[Depends(require_admin)])
def promote_user_to_admin(
    user_id: int,
    db_session: Session = Depends(get_db)
):
    """
    Promote a user to admin role (admin only).

    Args:
        user_id: ID of the user to promote
        db_session: Database session

    Returns:
        dict: Success message with user details

    Raises:
        HTTPException: If the user is not found
    """
    user = auth_operations.promote_user_to_admin(db_session, user_id)
    return {
        "status": "success",
        "user_id": user_id,
        "role": user.role.value
    }
