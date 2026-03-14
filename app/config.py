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


# ==============================
# PROJECT PATHS
# ==============================

BASE_DIR = Path(__file__).resolve().parent.parent

MEDIA_DIR = BASE_DIR / "media"
SONGS_DIR = MEDIA_DIR / "songs"
THUMBNAILS_DIR = MEDIA_DIR / "thumbnails"

# Ensure folders exist
SONGS_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)


# ==============================
# API CONFIGURATION
# ==============================

API_V1_PREFIX = "/api"


# ==============================
# GOOGLE AUTH CONFIG
# ==============================

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:5173/auth/google/callback"
)


# ==============================
# EMAIL CONFIGURATION
# ==============================

EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

SMTP_FROM = SMTP_USER


# ==============================
# SETTINGS CLASS
# ==============================

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
    def GOOGLE_CLIENT_ID(self) -> Optional[str]:
        return GOOGLE_CLIENT_ID

    @property
    def GOOGLE_CLIENT_SECRET(self) -> Optional[str]:
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