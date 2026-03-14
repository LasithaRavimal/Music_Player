import logging
from typing import Optional, Tuple
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings, refresh_email_config

logger = logging.getLogger(__name__)


# ---------------------------------
# GENERIC EMAIL SENDER
# ---------------------------------
async def send_email(to_email: str, subject: str, body_html: str, body_text: Optional[str] = None) -> bool:
    """
    Send email using SMTP
    """

    refresh_email_config()

    if not settings.EMAIL_ENABLED:
        logger.info(f"Email disabled. Would send to {to_email}")
        return False

    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured")
        return False

    try:

        smtp_host = settings.SMTP_HOST
        smtp_port = settings.SMTP_PORT
        smtp_user = settings.SMTP_USER
        smtp_password = settings.SMTP_PASSWORD
        smtp_from = settings.SMTP_FROM or smtp_user

        message = MIMEMultipart("alternative")
        message["Subject"] = subject

        from_address = smtp_from
        if "<" not in from_address:
            from_address = f"M_Track System <{from_address}>"

        message["From"] = from_address
        message["To"] = to_email

        if body_text:
            message.attach(MIMEText(body_text, "plain"))

        message.attach(MIMEText(body_html, "html"))

        # Gmail / SMTP configuration
        if smtp_port == 465:

            await aiosmtplib.send(
                message,
                hostname=smtp_host,
                port=smtp_port,
                username=smtp_user,
                password=smtp_password,
                use_tls=True,
            )

        else:

            await aiosmtplib.send(
                message,
                hostname=smtp_host,
                port=smtp_port,
                username=smtp_user,
                password=smtp_password,
                use_tls=False,
                start_tls=True,
            )

        logger.info(f"Email sent to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Email sending failed: {e}")
        return False


# ---------------------------------
# WELCOME EMAIL
# ---------------------------------
def create_welcome_email_body(user_email: str, user_name: Optional[str] = None) -> Tuple[str, str]:

    display_name = user_name or user_email.split("@")[0]

    html_body = f"""
    <html>
    <body>
        <h2>Welcome to M_Track</h2>

        <p>Hello {display_name},</p>

        <p>
        Thank you for registering with <strong>M_Track</strong>.
        This system is developed for research purposes to analyze
        music listening behaviour and mental health indicators.
        </p>

        <h3>How the system works:</h3>

        <ul>
        <li>Complete PHQ-9 depression questionnaire</li>
        <li>Complete DASS-21 stress questionnaire</li>
        <li>Listen to music normally</li>
        <li>Your listening behaviour will be recorded</li>
        </ul>

        <p>
        Your data will help researchers understand relationships between
        music listening behaviour and mental health.
        </p>

        <p><strong>M_Track Research System</strong></p>

    </body>
    </html>
    """

    text_body = f"""
Welcome to M_Track

Hello {display_name},

Thank you for registering.

You will complete PHQ-9 and DASS-21 questionnaires and then listen to music.

Your listening behaviour will be recorded for research purposes.

Thank you for contributing to this study.

M_Track Research System
"""

    return html_body, text_body


async def send_welcome_email(user_email: str, user_name: Optional[str] = None) -> bool:

    subject = "Welcome to M_Track Research Platform"

    html_body, text_body = create_welcome_email_body(user_email, user_name)

    return await send_email(user_email, subject, html_body, text_body)


# ---------------------------------
# QUESTIONNAIRE ALERT EMAIL
# ---------------------------------
def create_questionnaire_alert_email_body(
    user_email: str,
    stress_score: int,
    depression_score: int
) -> Tuple[str, str]:

    html_body = f"""
    <html>
    <body>

        <h2>M_Track Mental Health Alert</h2>

        <p>
        Your recent questionnaire results indicate elevated stress or depression levels.
        </p>

        <p><strong>PHQ-9 Depression Score:</strong> {depression_score}</p>
        <p><strong>DASS-21 Stress Score:</strong> {stress_score}</p>

        <h3>Important Notice</h3>

        <p>
        If you are experiencing persistent stress or depression,
        please consider seeking support from a mental health professional.
        </p>

        <p>
        This alert is based on standardized psychological questionnaires
        used in mental health screening.
        </p>

        <p>
        M_Track Research System
        </p>

    </body>
    </html>
    """

    text_body = f"""
M_Track Mental Health Alert

Your questionnaire results indicate elevated stress or depression.

PHQ-9 Depression Score: {depression_score}
DASS-21 Stress Score: {stress_score}

If symptoms continue, please consider consulting a mental health professional.

M_Track Research System
"""

    return html_body, text_body


async def send_questionnaire_alert(
    user_email: str,
    stress_score: int,
    depression_score: int
) -> bool:

    subject = "M_Track Mental Health Alert"

    html_body, text_body = create_questionnaire_alert_email_body(
        user_email,
        stress_score,
        depression_score
    )

    return await send_email(user_email, subject, html_body, text_body)