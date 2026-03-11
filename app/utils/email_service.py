import logging
from typing import Optional, Tuple
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings, refresh_email_config

logger = logging.getLogger(__name__)


# ==============================
# GENERIC EMAIL SENDER
# ==============================
async def send_email(to_email: str, subject: str, body_html: str, body_text: Optional[str] = None) -> bool:

    refresh_email_config()

    if not settings.EMAIL_ENABLED:
        logger.info("Email sending disabled")
        return False

    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP credentials missing")
        return False

    try:

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"M_Track System <{settings.SMTP_USER}>"
        message["To"] = to_email

        if body_text:
            message.attach(MIMEText(body_text, "plain"))

        message.attach(MIMEText(body_html, "html"))

        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True
        )

        logger.info(f"Email sent to {to_email}")

        return True

    except Exception as e:
        logger.error(f"Email failed: {str(e)}")
        return False


# ==============================
# WELCOME EMAIL
# ==============================
def create_welcome_email_body(user_email: str, user_name: Optional[str] = None) -> Tuple[str, str]:

    name = user_name or user_email.split("@")[0]

    html = f"""
    <html>
    <body style="font-family: Arial">

    <h2>Welcome to M_Track</h2>

    <p>Hello {name},</p>

    <p>
    Thank you for registering in <b>M_Track</b>.
    This platform collects music listening behaviour to help
    analyze mental wellbeing patterns.
    </p>

    <p>You can now start listening to music in the player.</p>

    <p>Your listening behaviour will be recorded anonymously for research.</p>

    <p>Thank you for participating.</p>

    <p><b>M_Track Team</b></p>

    </body>
    </html>
    """

    text = f"""
Welcome to M_Track

Hello {name},

Thank you for registering.

You can now start listening to music using the player.
Your listening behaviour will be collected for research purposes.

M_Track Team
"""

    return html, text


async def send_welcome_email(user_email: str, user_name: Optional[str] = None) -> bool:

    subject = "Welcome to M_Track"

    html, text = create_welcome_email_body(user_email, user_name)

    return await send_email(user_email, subject, html, text)