"""
One-time, idempotent auth migration for CA-RAG.

Run from the backend/ folder (with the venv active), BEFORE or right after
deploying the new auth code:

    python scripts/migrate_auth.py --dry-run     # show what would change
    python scripts/migrate_auth.py               # apply

What it does (existing users, documents, chats and feedback are left as they are):
  1. Aborts without changing anything if two accounts have the same email
     ignoring case (a unique email index could not be created).
  2. Trims/lowercases stored emails.
  3. Creates indexes on `users`:
       - unique email, case-insensitive
       - unique username, only for users that have one (username is optional)
       - reset_token_hash lookup index (only for users with a pending reset)
"""
import argparse
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import ASCENDING, MongoClient  # noqa: E402

from app.config import settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    args = parser.parse_args()

    users = MongoClient(settings.mongodb_uri)[settings.mongodb_db]["users"]

    by_email = defaultdict(list)
    to_normalize = []
    total = 0
    for u in users.find({}, {"email": 1}):
        total += 1
        raw = u.get("email") or ""
        norm = raw.strip().lower()
        by_email[norm].append(str(u["_id"]))
        if raw != norm:
            to_normalize.append((u["_id"], norm))

    duplicates = {e: ids for e, ids in by_email.items() if len(ids) > 1}
    print(f"users found: {total}")
    if duplicates:
        print("\nABORTED: these emails are used by more than one account (ignoring case):")
        for email, ids in duplicates.items():
            print(f"  {email}: user ids {ids}")
        print("Merge or delete the extra accounts, then run this script again. Nothing was changed.")
        return 1

    print(f"emails to trim/lowercase: {len(to_normalize)}")
    if args.dry_run:
        print("dry run -- no changes made.")
        return 0

    for _id, norm in to_normalize:
        users.update_one({"_id": _id}, {"$set": {"email": norm}})

    users.create_index(
        [("email", ASCENDING)],
        name="uniq_email_ci",
        unique=True,
        collation={"locale": "en", "strength": 2},
    )
    users.create_index(
        [("username", ASCENDING)],
        name="uniq_username",
        unique=True,
        partialFilterExpression={"username": {"$type": "string"}},
    )
    users.create_index(
        [("reset_token_hash", ASCENDING)],
        name="reset_token_hash_idx",
        partialFilterExpression={"reset_token_hash": {"$type": "string"}},
    )
    print("done: emails normalised, indexes ensured.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
