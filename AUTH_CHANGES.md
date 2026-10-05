# CA-RAG authentication update

Adds the Login System's forgot/reset-password flow and username-or-email login to CA-RAG.
The RAG pipeline (`backend/app/services/**`), all CSS, and the frontend package files are unchanged.
No Tailwind was added.

## Upgrade steps (from `backend/`, venv active)

1. `pip install -r requirements.txt`  (only change: `bcrypt==4.0.1` pinned for passlib 1.7.4)
2. Edit your existing `backend/.env` -- add the new variables (see `.env.example`):
   - `JWT_SECRET` -> set a real random value (`python -c "import secrets; print(secrets.token_hex(48))"`).
     Everyone is logged out once when you change it.
   - `FRONTEND_URL=http://localhost:5173`
   - `EMAIL_USER`, `EMAIL_PASS` (Gmail: an *app password*), optional `SMTP_HOST`, `SMTP_PORT`
   - optional `MIN_PASSWORD_LENGTH` (default 8), `RESET_TOKEN_EXPIRE_MINUTES` (default 10)
3. `python scripts/migrate_auth.py --dry-run`, then `python scripts/migrate_auth.py`
   (lowercases stored emails, creates the unique indexes; existing users/documents/chats are kept).
4. Start the backend and frontend as usual.
5. Optional checks: `pytest` (unit tests) and `python scripts/smoke_test_auth.py [--with-chat]`
   (end-to-end auth + user-isolation test; cleans up after itself).

## API changes (all backward compatible)

| Endpoint | Change |
|---|---|
| `POST /api/auth/register` | optional `username`; password min 8 (max 72 bytes); emails lowercased; validation errors are 400 with a string `detail` |
| `POST /api/auth/login` | accepts `identifier` (email or username) or legacy `email`; bad credentials -> **400** `Invalid credentials` (was 401) |
| `GET /api/auth/me` | also returns `username` |
| `POST /api/auth/forgot-password` | new -- same response whether or not the email exists |
| `POST /api/auth/reset-password/{token}` | new -- single use, expires after 10 min, invalidates older JWTs |
| `POST /api/auth/logout` | unchanged |

Responses keep the existing shape (`access_token`, `token_type`, `user`), now with `user.username`.

## Database (`users` collection)

New optional fields: `username`, `reset_token_hash` (SHA-256 of the emailed token; the raw token is never stored),
`reset_token_expiry`, `password_changed_at`. Indexes: unique case-insensitive `email`, unique `username`
(only where set), `reset_token_hash` lookup. `_id`, `name`, `email`, `password_hash`, `created_at` are unchanged,
so every existing document/message/feedback row still points at the right user.

## User-isolation fixes

- Feedback: the rated message must be an assistant message owned by the caller, and `used_chunks` must come from that answer.
- Deleting a document now also deletes its chat messages and their feedback (they used to be orphaned).
- Malformed ids in tokens / document ids / message ids now return 401/404 instead of 500.

## Frontend

- `Login.jsx`: "Email or username" field, "Forgot password?" link
- `Register.jsx`: optional "Username" field
- New pages `ForgotPassword.jsx`, `ResetPassword.jsx` (existing CSS classes only) + two routes in `App.jsx`
- `authApi.js`: `login(identifier, password)`, `register(..., username)`, `forgotPassword`, `resetPassword`

## Things to know

- Logout is client-side (as in both projects). JWTs are stateless: a token someone copied stays valid until it
  expires (24 h, `JWT_EXPIRE_MINUTES`) or the user resets their password.
- Existing users whose passwords are shorter than 8 characters can still log in; the rule applies to new registrations and resets.
- Reset emails need working SMTP credentials. Without them the request still succeeds and the backend logs a warning.
