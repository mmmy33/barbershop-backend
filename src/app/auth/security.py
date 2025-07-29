import secrets

from fastapi import HTTPException, status
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models.user import User

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60*24
RESET_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, expires_delta: timedelta | None = None):
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {
        "sub": str(user_id),
        "exp": expire
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def create_password_reset_token(user_id: int) -> tuple[str, str, datetime]:

    jti = secrets.token_urlsafe(32)
    expire = datetime.now(UTC) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "jti": jti,
        "type": "pwd_reset"
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, jti, expire


def verify_password_reset_token(token: str, db: Session) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


        if payload.get("type") != "pwd_reset":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid token type")

        user_id = int(payload["sub"])



        jti = payload["jti"]
        user = db.scalar(select(User)
             .where(User.id == user_id)
             .where(User.password_reset_jti.isnot(None))
             .where(User.password_reset_expires >= datetime.now(UTC))
            )





        if not user or not verify_password(jti, user.password_reset_jti) :
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired token")

        return user

    except JWTError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid token")