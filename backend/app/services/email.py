import logging
from typing import Optional

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to

    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            use_tls=settings.smtp_tls,
        )
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        raise


async def send_verification_email(to: str, full_name: Optional[str], token: str) -> None:
    verify_url = f"{settings.frontend_url}/verify-email?token={token}"
    name = full_name or "there"
    html = f"""
    <h2>Welcome to {settings.app_name}!</h2>
    <p>Hi {name},</p>
    <p>Please verify your email address by clicking the link below:</p>
    <p><a href="{verify_url}">Verify Email Address</a></p>
    <p>This link expires in 24 hours.</p>
    <p>If you did not create an account, please ignore this email.</p>
    """
    await send_email(to, f"Verify your email — {settings.app_name}", html)


async def send_password_reset_email(to: str, full_name: Optional[str], token: str) -> None:
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"
    name = full_name or "there"
    html = f"""
    <h2>Reset your password</h2>
    <p>Hi {name},</p>
    <p>We received a request to reset your password. Click the link below:</p>
    <p><a href="{reset_url}">Reset Password</a></p>
    <p>This link expires in 1 hour.</p>
    <p>If you did not request a password reset, please ignore this email.</p>
    """
    await send_email(to, f"Reset your password — {settings.app_name}", html)
