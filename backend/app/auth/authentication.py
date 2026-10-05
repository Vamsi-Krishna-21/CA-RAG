from datetime import timedelta
from typing import Optional

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.auth.security_utils import is_token_stale, utcnow
from app.config import settings
from app.database.mongodb import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Case-insensitive matching for email lookups (also used by the unique index created by
# scripts/migrate_auth.py), so "A@x.com" and "a@x.com" are the same account even for
# users registered before emails were lowercased.
EMAIL_COLLATION = {"locale": "en", "strength": 2}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        # e.g. password longer than bcrypt's 72-byte limit on newer bcrypt builds
        return False


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    now = utcnow()
    to_encode.update({"iat": now, "exp": now + timedelta(minutes=settings.jwt_expire_minutes)})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def parse_object_id(value: Optional[str]) -> Optional[ObjectId]:
    """Returns an ObjectId, or None if `value` is not a valid one (instead of raising -> 500)."""
    if value and ObjectId.is_valid(value):
        return ObjectId(value)
    return None


async def find_user_by_email(email: str) -> Optional[dict]:
    return await get_db().users.find_one({"email": email}, collation=EMAIL_COLLATION)


async def find_user_by_username(username: str) -> Optional[dict]:
    return await get_db().users.find_one({"username": username})


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Backend-side auth dependency. Every protected route depends on this,
    regardless of what the frontend's ProtectedRoute already checked --
    the frontend check is only for navigation/UX, never trusted for security.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise credentials_exception

    user_oid = parse_object_id(payload.get("sub"))
    if user_oid is None:
        raise credentials_exception

    db = get_db()
    user = await db.users.find_one({"_id": user_oid})
    if user is None:
        raise credentials_exception

    # A password reset invalidates every token issued before it.
    if is_token_stale(payload.get("iat"), user.get("password_changed_at")):
        raise credentials_exception

    user["id"] = str(user["_id"])
    return user
