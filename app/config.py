import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "m_track_db")

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 10080))

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent

MODELS_DIR = BASE_DIR / "app" / "models"
MEDIA_DIR = BASE_DIR / "media"

# Model paths
STRESS_MODEL_PATH = MODELS_DIR / "stress_model_catboost.cbm"
DEPRESSION_MODEL_PATH = MODELS_DIR / "depression_model_catboost.cbm"
MODEL_METADATA_PATH = MODELS_DIR / "model_metadata.pkl"

# Face model
FACE_MODEL_PATH = MODELS_DIR / "face_model.keras"
FACE_IMG_SIZE = int(os.getenv("FACE_IMG_SIZE", 224))
FACE_CLASS_NAMES = os.getenv("FACE_CLASS_NAMES", "Angry,Fear,Happy,Sad").split(",")

# Media paths
SONGS_DIR = MEDIA_DIR / "songs"
THUMBNAILS_DIR = MEDIA_DIR / "thumbnails"

SONGS_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# API
API_V1_PREFIX = "/api"

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:5173/auth/google/callback",
)

# Email
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = SMTP_USER


class Settings:
    @property
    def MONGO_URI(self):
        return MONGO_URI

    @property
    def DB_NAME(self):
        return DB_NAME

    @property
    def SECRET_KEY(self):
        return SECRET_KEY

    @property
    def ALGORITHM(self):
        return ALGORITHM

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self):
        return ACCESS_TOKEN_EXPIRE_MINUTES


settings = Settings()