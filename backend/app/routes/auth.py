from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from app.auth.authentication import (
    create_access_token,
    find_user_by_email,
    find_user_by_username,
    get_current_user,
    hash_password,
    verify_password,
)
from app.auth.email_service import send_password_reset_email
from app.auth.security_utils import (
    email_error,
    generate_reset_token,
    hash_reset_token,
    normalize_email,
    normalize_username,
    password_error,
    username_error,
    utcnow,
)
from app.config import settings
from app.database.mongodb import get_db
from app.models.user import new_user_doc
from app.schemas.auth_schema import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

FORGOT_PASSWORD_MESSAGE = "If that email is registered, a reset link has been sent"


def _bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail=message)


def _user_out(user: dict) -> UserOut:
    return UserOut(
        id=str(user["_id"]),
        name=user["name"],
        email=user["email"],
        username=user.get("username"),
    )


@router.post("/register", response_model=TokenResponse)
async def register(payload: RegisterRequest):
    name = payload.name.strip()
    email = normalize_email(payload.email)
    username = normalize_username(payload.username) or None

    if not name:
        raise _bad_request("Name is required")
    err = email_error(email)
    if err:
        raise _bad_request(err)
    if username:
        err = username_error(username)
        if err:
            raise _bad_request(err)
    err = password_error(payload.password, settings.min_password_length)
    if err:
        raise _bad_request(err)

    if await find_user_by_email(email):
        raise _bad_request("Email already registered")
    if username and await find_user_by_username(username):
        raise _bad_request("Username already taken")

    db = get_db()
    doc = new_user_doc(name, email, hash_password(payload.password), username)
    try:
        result = await db.users.insert_one(doc)
    except DuplicateKeyError:  # unique indexes from scripts/migrate_auth.py
        raise _bad_request("Email or username already registered")

    user_id = str(result.inserted_id)
    token = create_access_token({"sub": user_id})
    return TokenResponse(
        access_token=token,
        user=UserOut(id=user_id, name=name, email=email, username=username),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    # Accepts an email or a username (`identifier`); the old `email` field still works.
    identifier = normalize_email(payload.identifier or payload.email)
    if not identifier or not payload.password:
        raise _bad_request("Invalid credentials")

    # Usernames cannot contain "@", so this cleanly separates the two.
    if "@" in identifier:
        user = await find_user_by_email(identifier)
    else:
        user = await find_user_by_username(identifier)

    # 400 (not 401) on purpose: the frontend's axios interceptor treats every 401 as
    # "session expired" and hard-reloads the page, which would wipe this error message.
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise _bad_request("Invalid credentials")

    token = create_access_token({"sub": str(user["_id"])})
    return TokenResponse(access_token=token, user=_user_out(user))


@router.post("/logout")
async def logout():
    # Stateless JWT -- logout is handled client-side by discarding the token.
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)):
    return _user_out(current_user)


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    email = normalize_email(payload.email)
    if not email:
        raise _bad_request("Email is required")

    # Identical response whether or not the account exists (no account enumeration).
    response = {"detail": FORGOT_PASSWORD_MESSAGE, "message": FORGOT_PASSWORD_MESSAGE}

    user = await find_user_by_email(email)
    if user:
        raw_token, token_hash = generate_reset_token()
        expiry = utcnow() + timedelta(minutes=settings.reset_token_expire_minutes)
        await get_db().users.update_one(
            {"_id": user["_id"]},
            {"$set": {"reset_token_hash": token_hash, "reset_token_expiry": expiry}},
        )
        link = f"{settings.frontend_url.rstrip('/')}/reset-password/{raw_token}"
        background_tasks.add_task(send_password_reset_email, user["email"], link)

    return response


@router.post("/reset-password/{token}")
async def reset_password(token: str, payload: ResetPasswordRequest):
    err = password_error(payload.password, settings.min_password_length)
    if err:
        raise _bad_request(err)

    db = get_db()
    token_hash = hash_reset_token(token)
    now = utcnow()
    user = await db.users.find_one(
        {"reset_token_hash": token_hash, "reset_token_expiry": {"$gt": now}}
    )
    if not user:
        raise _bad_request("Invalid or expired token")

    # The filter re-checks the token hash, so two simultaneous requests cannot both succeed.
    result = await db.users.update_one(
        {"_id": user["_id"], "reset_token_hash": token_hash},
        {
            "$set": {"password_hash": hash_password(payload.password), "password_changed_at": now},
            "$unset": {"reset_token_hash": "", "reset_token_expiry": ""},
        },
    )
    if result.modified_count != 1:
        raise _bad_request("Invalid or expired token")

    return {"detail": "Password reset successful", "message": "Password reset successful"}
