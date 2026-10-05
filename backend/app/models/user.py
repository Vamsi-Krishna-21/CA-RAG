from datetime import datetime
from typing import Optional


def new_user_doc(name: str, email: str, password_hash: str, username: Optional[str] = None) -> dict:
    doc = {
        "name": name,
        "email": email,
        "password_hash": password_hash,
        "created_at": datetime.utcnow(),
    }
    # Optional. Only stored when provided so the partial unique index ignores users without one.
    if username:
        doc["username"] = username
    return doc

# Fields added later by the password-reset flow (set with $set / removed with $unset):
#   reset_token_hash, reset_token_expiry, password_changed_at
