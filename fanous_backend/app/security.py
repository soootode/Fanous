import os
import datetime as dt
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from . import models

SECRET_KEY = os.getenv("FANOUS_SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 30
PASSWORD_RESET_SCOPE = "password_reset"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str) -> str:
    expire = dt.datetime.utcnow() + dt.timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    # توکن بازیابی رمز نباید به‌عنوان توکن دسترسی پذیرفته شود
    if payload.get("scope") == PASSWORD_RESET_SCOPE:
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) else None


def create_password_reset_token(email: str) -> str:
    """توکن JWT با انقضای ۳۰ دقیقه و scope=password_reset تولید می‌کند."""
    expire = dt.datetime.utcnow() + dt.timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": email, "exp": expire, "scope": PASSWORD_RESET_SCOPE}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_password_reset_token(token: str) -> Optional[str]:
    """در صورت اعتبار توکن، ایمیل کاربر را برمی‌گرداند؛ در غیر این صورت None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if payload.get("scope") != PASSWORD_RESET_SCOPE:
        return None
    email = payload.get("sub")
    return email if isinstance(email, str) and "@" in email else None


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="ورود شما منقضی شده یا نامعتبره — دوباره وارد شو.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise unauthorized
    user_id = decode_token(token)
    if not user_id:
        raise unauthorized
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise unauthorized
    return user
