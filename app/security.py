from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from collections import defaultdict, deque
import time

from .database import get_db
from . import models


SECRET_KEY = "supersecretkey123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def verify_password(plain_password, hashed_password):
    """
    verify_password function will verify that the provided
    plain password matches the stored hashed password.

    Returns:
        Returns True if passwords match, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """
    get_password_hash function will hash a plain password
    using bcrypt for secure storage.

    Returns:
        Returns the hashed password string.
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    create_access_token function will create a
    JWT access token with optional expiration.

    Returns:
        Returns the encoded JWT token as a string.
    """
    to_encode = data.copy()
    expire = datetime.utcnow()\
        + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
        ):
    """
    get_current_user function will retrieve the currently
    authenticated user from the provided JWT token.

    Raises 401 if the token is invalid or the user does not exist.
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
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user


def require_admin(current_user: models.User = Depends(get_current_user)):
    """
    require_admin function will ensure the current user has admin privileges.

    Raises 403 if the user is not an admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
            )
    return current_user


_WINDOW_SECONDS = 60
_MAX_CALLS = 60

_call_buckets = defaultdict(lambda: deque())


def rate_limit(
        request: Request,
        current_user: models.User = Depends(get_current_user)
        ):
    """
    rate_limit function will limit the number of API
    requests per user or IP within a time window.

    Raises 429 if the rate limit is exceeded.
    """
    key = f"user:{current_user.id}"\
        if current_user else f"ip:{request.client.host}"
    now = time.time()
    dq = _call_buckets[key]
    # purge old
    while dq and now - dq[0] > _WINDOW_SECONDS:
        dq.popleft()
    if len(dq) >= _MAX_CALLS:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again soon."
            )
    dq.append(now)
