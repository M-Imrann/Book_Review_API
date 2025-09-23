from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from collections import defaultdict, deque
from passlib.context import CryptContext
import time
from app.database import get_db
from app import models


# Security configuration
SECRET_KEY = "supersecretkey123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify if a plain text password matches the hashed password.

    Args:
        plain_password: The password in plain text
        hashed_password: The hashed password from the database

    Returns:
        bool: True if passwords match, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Args:
        password: The password in plain text

    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Create a JWT access token with an optional expiration time.

    Args:
        data: The payload data to include in the token
        expires_delta: Optional custom expiration time

    Returns:
        str: The encoded JWT token
    """
    to_encode = data.copy()
    expire = datetime.utcnow()
    + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db_session: Session = Depends(get_db)
) -> models.User:
    """
    Retrieve the currently authenticated user from the JWT token.

    Args:
        token: The JWT token from the Authorization header
        db_session: The database session

    Returns:
        models.User: The authenticated user

    Raises:
        HTTPException: If the token is invalid or user doesn't exist
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db_session.query(models.User)\
        .filter(models.User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    return user


def require_admin(
        current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Ensure the current user has admin privileges.

    Args:
        current_user: The authenticated user

    Returns:
        models.User: The user if they are an admin

    Raises:
        HTTPException: If the user is not an admin
    """
    if current_user.role != models.UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to perform this action"
        )
    return current_user


# Rate limiting configuration
RATE_LIMIT_WINDOW_SECONDS = 60
MAX_REQUESTS_PER_WINDOW = 60

request_timestamps = defaultdict(lambda: deque())


def rate_limit(
    request: Request,
    current_user: models.User = Depends(get_current_user)
) -> None:
    """
    Limit the number of API requests per user or IP within a time window.

    Args:
        request: The incoming request
        current_user: The authenticated user

    Raises:
        HTTPException: If the rate limit is exceeded
    """
    identifier = f"user:{current_user.id}"\
        if current_user else f"ip:{request.client.host}"
    current_time = time.time()
    timestamps = request_timestamps[identifier]

    # Remove timestamps outside the current window
    while timestamps and current_time - timestamps[0]\
            > RATE_LIMIT_WINDOW_SECONDS:
        timestamps.popleft()

    if len(timestamps) >= MAX_REQUESTS_PER_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )

    timestamps.append(current_time)
