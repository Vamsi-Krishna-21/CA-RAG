"""
Dependency-free helpers for authentication: input normalisation/validation,
password-reset tokens, and the "was this JWT issued before the password
changed?" check. Kept free of FastAPI/Mongo imports so they are trivially
unit-testable.

Validation functions return an error message (str) or None. Routes turn a
message into HTTPException(400, detail=<str>) -- deliberately NOT pydantic
constraints, because a pydantic 422 returns `detail` as a list and the
frontend renders `detail` directly as text.
"""
import calendar
import hashlib
import re
import secrets
from datetime import datetime, timezone
from typing import Optional, Tuple

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
# No "@" allowed, so a username can never be mistaken for an email at login.
USERNAME_RE = re.compile(r"^[a-z0-9_.-]{3,30}$")
MAX_PASSWORD_BYTES = 72  # bcrypt only uses the first 72 bytes


def utcnow() -> datetime:
    """Naive UTC datetime (what the rest of the project stores in Mongo)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_email(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def normalize_username(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def email_error(email: str) -> Optional[str]:
    if not email:
        return "Email is required"
    if not EMAIL_RE.match(email):
        return "Invalid email address"
    return None


def username_error(username: str) -> Optional[str]:
    if not USERNAME_RE.match(username):
        return "Username must be 3-30 characters: letters, numbers, . _ -"
    return None


def password_error(password: Optional[str], min_length: int) -> Optional[str]:
    if not password or len(password) < min_length:
        return f"Password must be at least {min_length} characters"
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return f"Password must be at most {MAX_PASSWORD_BYTES} bytes"
    return None


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_reset_token() -> Tuple[str, str]:
    """Returns (raw_token_for_the_email_link, sha256_hash_to_store)."""
    raw = secrets.token_hex(32)
    return raw, hash_reset_token(raw)


def is_token_stale(token_iat: Optional[int], password_changed_at: Optional[datetime]) -> bool:
    """
    True if the JWT was issued before the user's last password change.
    Tokens with no `iat` (issued before this feature) count as issued at 0,
    so they are rejected only for users who have since reset their password.
    """
    if password_changed_at is None:
        return False
    changed_ts = calendar.timegm(password_changed_at.utctimetuple())
    return (token_iat or 0) < changed_ts
