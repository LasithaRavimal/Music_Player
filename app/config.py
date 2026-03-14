import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ==============================
# DATABASE CONFIGURATION
# ==============================

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "mpData")

if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set")

# ==============================
# JWT AUTH CONFIGURATION
# ==============================

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not set")

ALGORITHM = os.getenv("ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080")
)  # 7 days



# -----------------------------------
# BASE PATHS
# -----------------------------------

BASE_DIR = Path(__file__).parent.parent

MEDIA_DIR = BASE_DIR / "media"

SONGS_DIR = MEDIA_DIR / "songs"

THUMBNAILS_DIR = MEDIA_DIR / "thumbnails"

SONGS_DIR.mkdir(parents=True, exist_ok=True)

THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------------
# API CONFIG
# -----------------------------------

API_V1_PREFIX = "/api"


# -----------------------------------
# GOOGLE OAUTH
# -----------------------------------

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:5173/auth/google/callback"
)


# -----------------------------------
# EMAIL CONFIGURATION
# -----------------------------------

_EMAIL_ENABLED_DEFAULT = os.getenv("EMAIL_ENABLED", "false").lower() == "true"

_SMTP_HOST_DEFAULT = os.getenv("SMTP_HOST", "smtp.gmail.com")

_SMTP_PORT_DEFAULT = int(os.getenv("SMTP_PORT", "587"))

_SMTP_USER_DEFAULT = os.getenv("SMTP_USER")

_SMTP_PASSWORD_DEFAULT = os.getenv("SMTP_PASSWORD")


EMAIL_ENABLED = _EMAIL_ENABLED_DEFAULT

SMTP_HOST = _SMTP_HOST_DEFAULT

SMTP_PORT = _SMTP_PORT_DEFAULT

SMTP_USER = _SMTP_USER_DEFAULT

SMTP_PASSWORD = _SMTP_PASSWORD_DEFAULT

SMTP_FROM = _SMTP_USER_DEFAULT


def load_email_config_from_db():

    global EMAIL_ENABLED, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM

    try:

        from app.db import get_db, EMAIL_CONFIG_COLLECTION

        db = get_db()

        config = db[EMAIL_CONFIG_COLLECTION].find_one(sort=[("updated_at", -1)])

        if config:

            EMAIL_ENABLED = config.get("enabled", _EMAIL_ENABLED_DEFAULT)

            SMTP_HOST = config.get("smtp_host", _SMTP_HOST_DEFAULT)

            SMTP_PORT = config.get("smtp_port", _SMTP_PORT_DEFAULT)

            SMTP_USER = config.get("smtp_user", _SMTP_USER_DEFAULT)

            SMTP_PASSWORD = config.get("smtp_password", _SMTP_PASSWORD_DEFAULT)

            SMTP_FROM = config.get("smtp_from", SMTP_USER or _SMTP_USER_DEFAULT)

    except Exception:

        EMAIL_ENABLED = _EMAIL_ENABLED_DEFAULT

        SMTP_HOST = _SMTP_HOST_DEFAULT

        SMTP_PORT = _SMTP_PORT_DEFAULT

        SMTP_USER = _SMTP_USER_DEFAULT

        SMTP_PASSWORD = _SMTP_PASSWORD_DEFAULT

        SMTP_FROM = _SMTP_USER_DEFAULT


def refresh_email_config():

    load_email_config_from_db()


# -----------------------------------
# SETTINGS CLASS
# -----------------------------------

class Settings:

    @property
    def MONGO_URI(self) -> str:
        return MONGO_URI

    @property
    def DB_NAME(self) -> str:
        return DB_NAME

    @property
    def SECRET_KEY(self) -> str:
        return SECRET_KEY

    @property
    def ALGORITHM(self) -> str:
        return ALGORITHM

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        return ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def SONGS_DIR(self) -> Path:
        return SONGS_DIR

    @property
    def THUMBNAILS_DIR(self) -> Path:
        return THUMBNAILS_DIR

    @property
    def API_V1_PREFIX(self) -> str:
        return API_V1_PREFIX

    @property
    def GOOGLE_CLIENT_ID(self) -> str:
        return GOOGLE_CLIENT_ID

    @property
    def GOOGLE_CLIENT_SECRET(self) -> str:
        return GOOGLE_CLIENT_SECRET

    @property
    def GOOGLE_REDIRECT_URI(self) -> str:
        return GOOGLE_REDIRECT_URI

    @property
    def EMAIL_ENABLED(self) -> bool:
        return EMAIL_ENABLED

    @property
    def SMTP_HOST(self) -> str:
        return SMTP_HOST

    @property
    def SMTP_PORT(self) -> int:
        return SMTP_PORT

    @property
    def SMTP_USER(self) -> Optional[str]:
        return SMTP_USER

    @property
    def SMTP_PASSWORD(self) -> Optional[str]:
        return SMTP_PASSWORD

    @property
    def SMTP_FROM(self) -> Optional[str]:
        return SMTP_FROM


settings = Settings()