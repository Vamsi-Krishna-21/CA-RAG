import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("uvicorn.error")


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    """
    Blocking SMTP send -- schedule it with FastAPI BackgroundTasks (which runs
    sync functions in a thread pool) so the HTTP request is not held up.
    Never raises: failures are logged server-side only, so the forgot-password
    response can never reveal whether an account exists.
    """
    if not settings.email_user or not settings.email_pass:
        logger.warning("EMAIL_USER / EMAIL_PASS not configured -- password reset email was not sent.")
        return

    msg = EmailMessage()
    msg["Subject"] = "Password Reset"
    msg["From"] = settings.email_user
    msg["To"] = to_email
    msg.set_content(
        "Click this link to reset your CA-RAG password:\n\n"
        f"{reset_link}\n\n"
        f"This link expires in {settings.reset_token_expire_minutes} minutes.\n"
        "If you did not request this, you can ignore this email."
    )

    try:
        context = ssl.create_default_context()
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15, context=context) as server:
                server.login(settings.email_user, settings.email_pass)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                server.starttls(context=context)
                server.login(settings.email_user, settings.email_pass)
                server.send_message(msg)
    except Exception as exc:  # noqa: BLE001 -- must not leak to the caller
        logger.error("Failed to send password reset email: %s", exc)
