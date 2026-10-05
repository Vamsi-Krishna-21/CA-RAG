from typing import Optional

from pydantic import BaseModel

# Every field has a default and email is a plain str on purpose: validation is done
# in the routes and reported as HTTPException(400, detail="<message>"). With strict
# pydantic types FastAPI would answer 422 with `detail` as a *list*, which the
# frontend would try to render as text.


class RegisterRequest(BaseModel):
    name: str = ""
    email: str = ""
    username: Optional[str] = None
    password: str = ""


class LoginRequest(BaseModel):
    identifier: Optional[str] = None  # email OR username
    email: Optional[str] = None       # legacy field, still accepted
    password: str = ""


class ForgotPasswordRequest(BaseModel):
    email: str = ""


class ResetPasswordRequest(BaseModel):
    password: str = ""


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    username: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
