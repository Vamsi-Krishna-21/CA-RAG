"""Unit tests for the dependency-free auth helpers. Run with `pytest` from backend/."""
from datetime import datetime, timedelta

from app.auth.security_utils import (
    email_error,
    generate_reset_token,
    hash_reset_token,
    is_token_stale,
    normalize_email,
    normalize_username,
    password_error,
    username_error,
    utcnow,
)


def test_normalize():
    assert normalize_email("  A@Example.COM ") == "a@example.com"
    assert normalize_email(None) == ""
    assert normalize_username(" Bob_1 ") == "bob_1"


def test_email_validation():
    assert email_error("a@b.co") is None
    assert email_error("") == "Email is required"
    assert email_error("not-an-email") == "Invalid email address"
    assert email_error("a b@c.com") == "Invalid email address"


def test_username_validation():
    assert username_error("bob_1.x-y") is None
    assert username_error("ab") is not None          # too short
    assert username_error("a" * 31) is not None      # too long
    assert username_error("bob@x.com") is not None   # '@' would be ambiguous with an email at login
    assert username_error("bob smith") is not None


def test_password_validation():
    assert password_error("12345678", 8) is None
    assert "at least 8" in password_error("1234567", 8)
    assert password_error("", 8) is not None
    assert password_error(None, 8) is not None
    assert "at most 72" in password_error("a" * 73, 8)
    assert password_error("a" * 72, 8) is None


def test_reset_token_is_hashed_and_unique():
    raw1, h1 = generate_reset_token()
    raw2, h2 = generate_reset_token()
    assert raw1 != raw2 and h1 != h2
    assert len(raw1) == 64
    assert h1 == hash_reset_token(raw1)
    assert raw1 not in h1


def test_token_staleness():
    changed = datetime(2026, 1, 1, 12, 0, 0)  # naive UTC
    changed_ts = 1767268800  # 2026-01-01T12:00:00Z
    assert is_token_stale(123, None) is False                 # never reset -> never stale
    assert is_token_stale(changed_ts - 1, changed) is True    # issued before the reset
    assert is_token_stale(changed_ts, changed) is False       # issued at/after the reset
    assert is_token_stale(changed_ts + 60, changed) is False
    assert is_token_stale(None, changed) is True              # legacy token without iat


def test_utcnow_is_naive_and_current():
    now = utcnow()
    assert now.tzinfo is None
    assert abs(now - datetime.utcnow()) < timedelta(seconds=5)
